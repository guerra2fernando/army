type ChatRole = "system" | "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

type ChatRequest = {
  messages: ChatMessage[];
  temperature?: number;
  max_completion_tokens?: number;
  max_tokens?: number;
  response_format?: { type: "text" | "json_object" };
  model?: string;
};

type AIResult = {
  response?: string;
  output_text?: string;
  usage?: Record<string, unknown>;
};

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function jsonResponse(body: unknown, status = 200, requestId?: string): Response {
  const headers = new Headers(JSON_HEADERS);
  if (requestId) headers.set("x-request-id", requestId);
  return new Response(JSON.stringify(body), { status, headers });
}

function configuredNumber(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function isChatMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== "object") return false;
  const message = value as Record<string, unknown>;
  return (
    (message.role === "system" || message.role === "user" || message.role === "assistant") &&
    typeof message.content === "string" &&
    message.content.length <= 1_000_000
  );
}

function timingSafeTextEqual(expected: string, actual: string): boolean {
  const encoder = new TextEncoder();
  const expectedBytes = encoder.encode(expected);
  const actualBytes = encoder.encode(actual);
  const size = Math.max(expectedBytes.byteLength, actualBytes.byteLength);
  const left = new Uint8Array(size);
  const right = new Uint8Array(size);
  left.set(expectedBytes);
  right.set(actualBytes);
  return expectedBytes.byteLength === actualBytes.byteLength && crypto.subtle.timingSafeEqual(left, right);
}

async function readBoundedBody(request: Request, maxBytes: number): Promise<string | null> {
  const contentLength = request.headers.get("content-length");
  if (contentLength && Number(contentLength) > maxBytes) return null;
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) return null;
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const combined = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(combined);
}

function validateChatRequest(value: unknown, maxTokens: number): ChatRequest | null {
  if (!value || typeof value !== "object") return null;
  const body = value as Record<string, unknown>;
  if (!Array.isArray(body.messages) || body.messages.length === 0 || body.messages.length > 256) return null;
  if (!body.messages.every(isChatMessage)) return null;
  if (body.temperature !== undefined &&
      (typeof body.temperature !== "number" || !Number.isFinite(body.temperature) || body.temperature < 0 || body.temperature > 2)) return null;
  const requested = body.max_completion_tokens ?? body.max_tokens ?? 1024;
  if (typeof requested !== "number" || !Number.isInteger(requested) || requested < 1 || requested > maxTokens) return null;
  if (body.response_format !== undefined &&
      (!body.response_format || typeof body.response_format !== "object" ||
       !["text", "json_object"].includes((body.response_format as Record<string, unknown>).type as string))) return null;
  return {
    messages: body.messages,
    temperature: body.temperature as number | undefined,
    max_completion_tokens: requested,
    response_format: body.response_format as ChatRequest["response_format"],
  };
}

function isAIResult(value: unknown): value is AIResult {
  return Boolean(value && typeof value === "object");
}

async function handleChat(request: Request, env: Env, requestId: string): Promise<Response> {
  const authorization = request.headers.get("authorization") ?? "";
  const supplied = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!env.CLOUDFLARE_AI_GATEWAY_TOKEN || !timingSafeTextEqual(env.CLOUDFLARE_AI_GATEWAY_TOKEN, supplied)) {
    return jsonResponse({ error: { message: "Unauthorized", type: "invalid_request_error" } }, 401, requestId);
  }

  const maxBytes = configuredNumber(env.MAX_REQUEST_BYTES, 5_242_880);
  const bodyText = await readBoundedBody(request, maxBytes);
  if (bodyText === null) return jsonResponse({ error: { message: "Request body too large", type: "invalid_request_error" } }, 413, requestId);

  let parsed: unknown;
  try { parsed = JSON.parse(bodyText); } catch { return jsonResponse({ error: { message: "Invalid JSON", type: "invalid_request_error" } }, 400, requestId); }
  const body = validateChatRequest(parsed, configuredNumber(env.MAX_COMPLETION_TOKENS, 8192));
  if (!body) return jsonResponse({ error: { message: "Invalid chat request", type: "invalid_request_error" } }, 400, requestId);

  const started = Date.now();
  try {
    const result: unknown = await env.AI.run(env.AI_MODEL, {
      messages: body.messages,
      temperature: body.temperature ?? 0.7,
      max_tokens: body.max_completion_tokens,
      ...(body.response_format ? { response_format: body.response_format } : {}),
    });
    if (!isAIResult(result)) throw new Error("invalid upstream response");
    const content = result.response ?? result.output_text;
    if (typeof content !== "string") throw new Error("missing upstream response");
    console.log(JSON.stringify({ request_id: requestId, status: 200, latency_ms: Date.now() - started, usage: result.usage ?? null }));
    return jsonResponse({
      id: `chatcmpl-${requestId}`,
      object: "chat.completion",
      created: Math.floor(Date.now() / 1000),
      model: env.AI_MODEL,
      choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
      ...(result.usage ? { usage: result.usage } : {}),
    }, 200, requestId);
  } catch (error) {
    const status = typeof error === "object" && error !== null && "status" in error ? (error as { status?: unknown }).status : undefined;
    const mapped = status === 429 ? 429 : status === 503 || status === 502 || status === 504 ? 503 : 500;
    console.error(JSON.stringify({ request_id: requestId, status: mapped, latency_ms: Date.now() - started }));
    return jsonResponse({ error: { message: "Inference service unavailable", type: "server_error" } }, mapped, requestId);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const requestId = crypto.randomUUID();
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      return jsonResponse({ service: "army-ai", status: "healthy" }, 200, requestId);
    }
    if (request.method === "POST" && url.pathname === "/v1/chat/completions") {
      return handleChat(request, env, requestId);
    }
    return jsonResponse({ error: { message: "Not found", type: "not_found" } }, 404, requestId);
  },
} satisfies ExportedHandler<Env>;
