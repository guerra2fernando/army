import { describe, expect, it, vi } from "vitest";
import worker from "../src/index";

const run = vi.fn(async () => ({ response: "ok", usage: { total_tokens: 2 } }));
const testEnv = {
  AI: { run } as unknown as Ai,
  AI_MODEL: "@cf/deepseek-ai/deepseek-v4-pro-0813",
  MAX_COMPLETION_TOKENS: "8192",
  MAX_REQUEST_BYTES: "5242880",
  CLOUDFLARE_AI_GATEWAY_TOKEN: "test-gateway-token",
} satisfies Env;

describe("army-ai gateway", () => {
  it("returns a minimal health response", async () => {
    const response = await worker.fetch(new Request("https://ai.test/health"), testEnv);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ service: "army-ai", status: "healthy" });
  });

  it("rejects missing and invalid authentication", async () => {
    const request = new Request("https://ai.test/v1/chat/completions", { method: "POST", body: "{}" });
    expect((await worker.fetch(request, testEnv)).status).toBe(401);
    const invalid = new Request(request, { headers: { authorization: "Bearer wrong" } });
    expect((await worker.fetch(invalid, testEnv)).status).toBe(401);
  });

  it("validates malformed JSON and messages", async () => {
    const headers = { authorization: "Bearer test-gateway-token" };
    const invalidJson = new Request("https://ai.test/v1/chat/completions", { method: "POST", headers, body: "{" });
    expect((await worker.fetch(invalidJson, testEnv)).status).toBe(400);
    const invalidMessages = new Request("https://ai.test/v1/chat/completions", {
      method: "POST", headers, body: JSON.stringify({ messages: [{ role: "tool", content: "bad" }] }),
    });
    expect((await worker.fetch(invalidMessages, testEnv)).status).toBe(400);
  });

  it("pins the model and normalizes successful inference", async () => {
    run.mockClear();
    const request = new Request("https://ai.test/v1/chat/completions", {
      method: "POST",
      headers: { authorization: "Bearer test-gateway-token", "content-type": "application/json" },
      body: JSON.stringify({ model: "client-selected-model", messages: [{ role: "user", content: "Reply ok" }], max_completion_tokens: 16 }),
    });
    const response = await worker.fetch(request, testEnv);
    expect(response.status).toBe(200);
    expect((await response.json())).toMatchObject({ object: "chat.completion", model: testEnv.AI_MODEL, choices: [{ message: { content: "ok" } }] });
    expect(run).toHaveBeenCalledWith(testEnv.AI_MODEL, expect.objectContaining({ max_tokens: 16 }));
  });

  it("preserves JSON response mode and rejects oversized bodies", async () => {
    const jsonRequest = new Request("https://ai.test/v1/chat/completions", {
      method: "POST",
      headers: { authorization: "Bearer test-gateway-token", "content-type": "application/json" },
      body: JSON.stringify({ messages: [{ role: "user", content: "{}" }], response_format: { type: "json_object" } }),
    });
    expect((await worker.fetch(jsonRequest, testEnv)).status).toBe(200);
    expect(run).toHaveBeenLastCalledWith(testEnv.AI_MODEL, expect.objectContaining({ response_format: { type: "json_object" } }));
    const oversized = new Request("https://ai.test/v1/chat/completions", { method: "POST", headers: { authorization: "Bearer test-gateway-token", "content-length": "6000000" }, body: "{}" });
    expect((await worker.fetch(oversized, testEnv)).status).toBe(413);
  });
});
