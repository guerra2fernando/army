# ArmLenQuant deployment plan: Scalingo + Cloudflare Workers AI

Status: implementation-ready plan
Prepared: 2026-09-01
Primary hostname: `army.lengrowth.com`

## 1. Outcome and architecture decision

Deploy the existing split-brain system without rewriting it:

```text
Browser
  |
  | HTTPS
  v
Cloudflare DNS/CDN/WAF
  |-- army.lengrowth.com --------> Scalingo: army-web (Next.js)
  |-- api.army.lengrowth.com ----> Scalingo: army-api (FastAPI, one web container)
  `-- ai.army.lengrowth.com -----> Cloudflare Worker: army-ai
                                         |
                                         `-> Workers AI binding
                                             @cf/deepseek-ai/deepseek-v4-pro-0813

Windows PC
  |-- local poller ----------------HTTPS----> api.army.lengrowth.com
  `-- local agents ----------------HTTPS----> ai.army.lengrowth.com

army-api --------------------------HTTPS----> ai.army.lengrowth.com
army-api --------------------------TLS------> MongoDB Atlas
```

Decisions:

1. Run the FastAPI API and Next.js dashboard as two Scalingo apps from the same repository using `PROJECT_DIR`.
2. Keep MongoDB Atlas. This repository uses Atlas Search/vector-search setup; switching to a Scalingo MongoDB add-on is a separate data-platform project.
3. Put the main chat model behind a small authenticated Worker using a Workers AI binding. This keeps Cloudflare account credentials out of Scalingo and the Windows poller, gives both runtimes one stable API, and makes rollback provider-controlled.
4. Use `@cf/deepseek-ai/deepseek-v4-pro-0813` as the primary chat model. It requires Workers Paid or prepaid AI Gateway credits.
5. Do not migrate embeddings in the first release. The current Atlas vectors are 1,536 dimensions and are generated through OpenAI. Changing embedding models requires a new vector index and complete re-ingestion. Chat inference and embeddings must have separate provider settings.
6. Keep exactly one FastAPI web container initially. The scheduler and Telegram bot start inside the FastAPI lifespan, so multiple web containers would duplicate scheduled work.

## 2. Verified repository facts and release blockers

The implementing AI must resolve these before creating production resources:

- Cloud API: `armlenquant-cloud/api`, FastAPI, MongoDB/Motor, in-process scheduler and optional Telegram bot.
- Dashboard: `armlenquant-cloud/dashboard`, Next.js 16.
- Local runtime: `armlenquant-local`, Python poller and local agents.
- Both cloud and local runtimes have separate copies of `agents/llm_client.py`; both must be migrated and tested.
- `armlenquant-cloud/dashboard/src/lib/` is ignored by the root `lib/` rule and is not tracked. A fresh Scalingo checkout will fail because `@/lib/api` and `@/lib/utils` will be absent.
- `armlenquant-cloud/dashboard/.env.example` is ignored by the dashboard `.env*` rule and is not tracked.
- There is no Scalingo `Procfile`, no Python version file, and the Next.js start command does not bind to Scalingo's `$PORT`.
- The API CORS configuration is `allow_origins=["*"]` together with credentials. Production must allow only the dashboard origin.
- `pytz` is imported directly by `app/main.py` but is not a direct API requirement.
- The Scalingo CLI is authenticated and can see the account's existing apps, but installed version `1.47.0` should be updated to `1.48.0` before mutation.
- No global `wrangler` command currently resolves. Install Wrangler 4.x as a dev dependency inside the new Worker project and call it with `npx wrangler`.

## 3. Names and configuration contract

Use these names unless one is already taken:

| Resource | Name |
|---|---|
| Scalingo project | `army` |
| Scalingo API app | `army-api` |
| Scalingo dashboard app | `army-web` |
| Cloudflare Worker | `army-ai` |
| Dashboard URL | `https://army.lengrowth.com` |
| API URL | `https://api.army.lengrowth.com` |
| AI gateway URL | `https://ai.army.lengrowth.com` |
| Workers AI model | `@cf/deepseek-ai/deepseek-v4-pro-0813` |
| Scalingo region | `osc-fr1` |

New application configuration:

| Variable | API | Local poller | Secret | Purpose |
|---|---:|---:|---:|---|
| `LLM_PROVIDER=cloudflare` | yes | yes | no | Select Workers AI chat client |
| `CLOUDFLARE_AI_BASE_URL=https://ai.army.lengrowth.com/v1` | yes | yes | no | Stable gateway base URL |
| `CLOUDFLARE_AI_GATEWAY_TOKEN` | yes | yes | yes | Shared bearer credential for the Worker |
| `CLOUDFLARE_AI_MODEL=@cf/deepseek-ai/deepseek-v4-pro-0813` | yes | yes | no | Expected model and telemetry label |
| `EMBEDDING_PROVIDER=openai` | yes | no | no | Decouple embeddings from the chat provider |
| `OPENAI_EMBEDDING_MODEL=text-embedding-3-small` | yes | no | no | Preserve 1,536-dimensional Atlas vectors |
| `CORS_ORIGINS=https://army.lengrowth.com` | yes | no | no | Exact browser origin allowlist |

Do not store any secret value in Git, Markdown, command history, logs, `wrangler.jsonc`, or `scalingo.json`. Enter Scalingo secrets in the Scalingo dashboard. Use the interactive `wrangler secret put` prompt for the Worker secret.

## 4. Execution rules for the implementing AI

The implementing AI must:

1. Work phase by phase and stop at every named gate.
2. Show `git status --short` before editing and preserve unrelated user changes.
3. Never read or print existing `.env` values. It may enumerate variable names only.
4. Never deploy from a dirty or uncommitted tree.
5. Never remove Gemini/OpenAI fallback credentials until the Workers AI canary has been stable for at least 24 hours.
6. Never scale `army-api` above one web container until the scheduler has a distributed lease or is moved to a separate process.
7. Never alter the existing Atlas vector index during the chat-model migration.
8. Record command output and URLs, but redact tokens, database URIs, JWT secrets, agent credentials, HMAC keys, and Telegram credentials.

## 5. Phase 0 — preflight and repository repair

### 5.1 Verify tools and accounts

Run read-only checks:

```powershell
git status --short
git remote -v
scalingo version
scalingo whoami
scalingo apps
node --version
npm --version
python --version
```

Update Scalingo CLI to the current supported release before running create/update commands. Do not install Wrangler globally.

Confirm in the Cloudflare dashboard:

- `lengrowth.com` is an active zone in the intended account.
- Workers Paid is active, or sufficient prepaid AI Gateway credits exist.
- `army`, `api.army`, and `ai.army` do not conflict with existing DNS records.

### 5.2 Fix tracked-file blockers

Change the root `.gitignore` so the generic Python `lib/` ignore does not hide dashboard source. Add explicit negations after the `lib/` rule:

```gitignore
!armlenquant-cloud/dashboard/src/lib/
!armlenquant-cloud/dashboard/src/lib/**
```

Change `armlenquant-cloud/dashboard/.gitignore` so the environment template is trackable:

```gitignore
!.env.example
```

Then explicitly add and verify:

```powershell
git add .gitignore armlenquant-cloud/dashboard/.gitignore `
  armlenquant-cloud/dashboard/src/lib/api.ts `
  armlenquant-cloud/dashboard/src/lib/utils.ts `
  armlenquant-cloud/dashboard/.env.example
git status --short
git check-ignore -v armlenquant-cloud/dashboard/src/lib/api.ts
```

`git check-ignore` must report that the file is not ignored.

### 5.3 Add Scalingo runtime files

In `armlenquant-cloud/api`:

- Add `.python-version` with `3.12` to avoid adopting Scalingo's newer default before this older dependency set is validated.
- Add `Procfile`:

```procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- Add `pytz` as a direct, pinned requirement.

In `armlenquant-cloud/dashboard/package.json`:

- Add `"engines": { "node": "22" }`.
- Change `start` to `next start -p $PORT`.

Do not add a Dockerfile. Scalingo's Python and Node buildpacks plus `PROJECT_DIR` are sufficient and easier to maintain.

### 5.4 Make CORS configurable

Add `cors_origins` to API settings and parse a comma-separated `CORS_ORIGINS`. In `app/main.py`, replace the wildcard with that setting. Expected production value:

```text
https://army.lengrowth.com
```

Keep localhost origins only in local `.env`/test configuration, not as production defaults. Add tests proving the production origin receives CORS headers and an unrelated origin does not.

### 5.5 Baseline verification

```powershell
Set-Location armlenquant-cloud/api
python -m pytest -q

Set-Location ../dashboard
npm ci
npm run lint
npm run build

Set-Location ../../armlenquant-local
python -m pytest -q
```

Gate 0: all tracked-file checks, API tests, local tests, dashboard lint, and dashboard build pass. Commit the repository-readiness changes before continuing.

## 6. Phase 1 — build the authenticated Workers AI gateway

Create `cloudflare/army-ai/` with:

```text
cloudflare/army-ai/
  package.json
  package-lock.json
  tsconfig.json
  wrangler.jsonc
  src/index.ts
  test/index.spec.ts
  README.md
```

Install current packages locally:

```powershell
Set-Location cloudflare/army-ai
npm init -y
npm install -D wrangler@latest typescript vitest @cloudflare/vitest-pool-workers @cloudflare/workers-types
npx wrangler --version
npx wrangler whoami
```

Use `wrangler.jsonc`, generate binding types with `npx wrangler types`, and configure:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "army-ai",
  "main": "src/index.ts",
  "compatibility_date": "2026-09-01",
  "compatibility_flags": ["nodejs_compat"],
  "ai": { "binding": "AI" },
  "routes": [
    { "pattern": "ai.army.lengrowth.com", "custom_domain": true }
  ],
  "vars": {
    "AI_MODEL": "@cf/deepseek-ai/deepseek-v4-pro-0813",
    "MAX_COMPLETION_TOKENS": "8192",
    "MAX_REQUEST_BYTES": "5242880"
  },
  "observability": {
    "enabled": true,
    "head_sampling_rate": 1
  }
}
```

Before deploying, validate these keys against the installed Wrangler schema. If current docs/schema differ, use the current supported shape and document the difference.

### 6.1 Worker API contract

Implement:

- `GET /health` -> `200` JSON with service name and status only. Do not reveal secrets or account identifiers.
- `POST /v1/chat/completions` -> authenticated chat inference.
- All other methods/paths -> `404` JSON.

For the chat endpoint:

1. Require `Authorization: Bearer <CLOUDFLARE_AI_GATEWAY_TOKEN>`.
2. Compare credentials using a timing-safe Web Crypto comparison.
3. Reject absent/invalid auth with `401` and no detail.
4. Reject bodies over `MAX_REQUEST_BYTES` before buffering them.
5. Validate `messages`, roles, content, temperature, and token limit. Ignore or reject arbitrary client-provided model names; the server-side `AI_MODEL` is authoritative.
6. Call `env.AI.run(env.AI_MODEL, ...)` through the binding, not the Cloudflare REST API.
7. Support the current application's synchronous calls first. Streaming is not required for this migration.
8. Preserve JSON-mode requests where the selected model supports `response_format`.
9. Return a stable OpenAI-compatible response envelope so the existing Python `AsyncOpenAI` client can consume it.
10. Add `x-request-id`; log structured metadata such as status, latency, token usage, and request ID. Never log prompts, completions, authorization headers, or full request bodies.
11. Map invalid input to `400`, auth to `401`, rate/capacity errors to `429`/`503`, and unexpected failures to a generic `500`.

The Worker should not hold mutable request data at module scope, should await every promise, and should use the generated `Env` type.

### 6.2 Worker tests and deployment

Tests must cover health, missing auth, wrong auth, malformed input, oversized input, model pinning, successful normalization, JSON mode, and upstream error mapping. Mock the AI binding in unit tests.

```powershell
npm test
npx wrangler types --check
npx tsc --noEmit
npx wrangler deploy --dry-run
npx wrangler check startup
npx wrangler secret put CLOUDFLARE_AI_GATEWAY_TOKEN
npx wrangler deploy
npx wrangler tail army-ai
```

Use a newly generated random 32-byte-or-longer token. Store the same value in a password manager for later entry into Scalingo and the local poller's `.env`.

Smoke test without putting the token literally in shell history:

```powershell
$armyAiToken = Read-Host -MaskInput 'AI gateway token'
$headers = @{ Authorization = "Bearer $armyAiToken" }
Invoke-RestMethod https://ai.army.lengrowth.com/health
Invoke-RestMethod https://ai.army.lengrowth.com/v1/chat/completions `
  -Method Post `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body '{"messages":[{"role":"user","content":"Reply with exactly: ok"}],"max_completion_tokens":16}'
Remove-Variable armyAiToken
```

Gate 1: Worker tests pass; dry run and startup checks pass; custom domain resolves; unauthenticated inference is rejected; authenticated inference returns `ok`; logs contain no prompt or secret.

## 7. Phase 2 — migrate the Python chat clients

Implement the same provider in both:

- `armlenquant-cloud/api/app/agents/llm_client.py`
- `armlenquant-local/agents/llm_client.py`

Required changes:

1. Add `CLOUDFLARE = "cloudflare"` to `LLMProvider`.
2. Add a `CloudflareWorkersAIClient` implementing `BaseLLMClient`.
3. Reuse `openai.AsyncOpenAI` with:
   - `api_key=CLOUDFLARE_AI_GATEWAY_TOKEN`
   - `base_url=CLOUDFLARE_AI_BASE_URL`
   - model set to `CLOUDFLARE_AI_MODEL`
4. Translate the existing `max_tokens` argument to the endpoint's current supported completion-token field.
5. Keep `json_response=True` mapped to JSON-object response format and verify actual parsing with DeepSeek V4 Pro.
6. Add explicit HTTP timeouts and bounded retry/backoff for `429`, `502`, `503`, and `504` only.
7. Never retry `400`, `401`, or `403`; never fallback on authentication failures.
8. Make Cloudflare the selected primary provider when `LLM_PROVIDER=cloudflare`.
9. Keep Gemini/OpenAI as temporary emergency fallbacks for chat during the canary.
10. Redact authorization values and prompt contents from logs.

Update both configuration models and `.env.example` files with the new variables. Update provider error messages and documentation to list `cloudflare`.

### 7.1 Separate embeddings from chat

Refactor `armlenquant-cloud/api/app/rag/embeddings.py` to read `EMBEDDING_PROVIDER`, not `LLM_PROVIDER`. Preserve `openai` and `text-embedding-3-small` for this deployment. Add a startup/configuration error when a real embedding call is requested without its required credential; do not silently use a fake production key.

Do not change vector dimensions, Atlas Search index definitions, or stored vectors in this phase.

### 7.2 Migration tests

Add/update tests in both suites for:

- Cloudflare provider selection and availability.
- Base URL, bearer token, model, messages, temperature, token limit, and JSON mode mapping.
- Retry on transient status and no retry/fallback on auth status.
- Fallback from Cloudflare to the configured emergency provider on transient exhaustion.
- Embedding provider remains OpenAI when chat provider is Cloudflare.
- No credential appears in captured logs or exception strings.

Run both full Python suites. Then run one opt-in live smoke test against the deployed Worker; mark it so normal unit tests never incur Workers AI charges.

Gate 2: all unit tests pass; live chat smoke succeeds from both API and local client code; existing Atlas embedding query tests remain unchanged and pass.

## 8. Phase 3 — create and configure the Scalingo apps

### 8.1 Create resources

Confirm names are still free, then create a new Scalingo project named `army`, create both apps in `osc-fr1`, and place both apps in that project. If the installed CLI cannot create or select the project reliably, create the `army` project and place the apps in it through the Scalingo dashboard rather than guessing a flag.

```powershell
scalingo create army-api --region osc-fr1
scalingo create army-web --region osc-fr1
```

Link both apps to `https://github.com/guerra2fernando/army`, branch `main`, using the Scalingo GitHub integration. Leave automatic deployment disabled until the first verified manual deployment.

Set non-secret monorepo/build variables:

```powershell
scalingo --app army-api env-set PROJECT_DIR=armlenquant-cloud/api DEBUG=false LLM_PROVIDER=cloudflare EMBEDDING_PROVIDER=openai CORS_ORIGINS=https://army.lengrowth.com
scalingo --app army-web env-set PROJECT_DIR=armlenquant-cloud/dashboard NODE_ENV=production NEXT_PUBLIC_API_URL=https://api.army.lengrowth.com
```

Use the Scalingo dashboard to enter API secrets:

- `MONGODB_URI`
- `JWT_SECRET`
- `AGENT_SECRET`
- `CLOUDFLARE_AI_GATEWAY_TOKEN`
- `OPENAI_API_KEY` while embeddings and fallback require it
- `GEMINI_API_KEY` only if Gemini remains a canary fallback
- Optional crypto and Telegram credentials

Set remaining non-secret API values in the dashboard or CLI:

- `MONGODB_DB_NAME=armlenquant`
- `CLOUDFLARE_AI_BASE_URL=https://ai.army.lengrowth.com/v1`
- `CLOUDFLARE_AI_MODEL=@cf/deepseek-ai/deepseek-v4-pro-0813`
- `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`
- `LLM_AUTO_FALLBACK=true` during canary
- `MTLS_REQUIRED=false` unless Cloudflare-to-origin client-certificate forwarding has been deliberately implemented and tested
- `TELEGRAM_ENABLED=false` for the first boot; enable it after core health passes

### 8.2 Atlas network access

Resolve Scalingo's current egress addresses at deployment time; do not copy stale addresses from this plan:

```powershell
Resolve-DnsName egress.osc-fr1.scalingo.com -Type A
```

Add every returned `/32` address to the MongoDB Atlas Network Access allowlist with a descriptive label and review reminder. Do not use `0.0.0.0/0`. Confirm the Atlas database user has only the permissions the application needs and the URI requires TLS.

Verify existing text and vector search indexes using the repository scripts before cutover. Do not recreate an index if it already matches the committed configuration.

### 8.3 First deployment and process scale

Trigger manual deployments from GitHub after the readiness commit is on `main`. Watch both logs:

```powershell
scalingo --app army-api logs --follow
scalingo --app army-web logs --follow
```

Keep one API web container and one dashboard web container:

```powershell
scalingo --app army-api scale web:1
scalingo --app army-web scale web:1
```

Test the default Scalingo hostnames before DNS:

- API `/health` returns `200`.
- API startup connects to Atlas and creates/checks indexes without errors.
- API logs show one scheduler start, not duplicates.
- Dashboard loads and its compiled API URL is `https://api.army.lengrowth.com`.
- Login and one non-destructive authenticated API read work.

Gate 3: both Scalingo deployments are healthy on their default domains; Atlas connectivity works; dashboard contains tracked `src/lib` modules; one scheduler instance is running.

## 9. Phase 4 — Cloudflare DNS, TLS, and production cutover

Attach the domains in Scalingo:

```powershell
scalingo --app army-web domains-add army.lengrowth.com
scalingo --app army-api domains-add api.army.lengrowth.com
```

In Cloudflare DNS, add proxied CNAME records:

| Type | Name | Target | Proxy |
|---|---|---|---|
| CNAME | `army` | `army-web.osc-fr1.scalingo.io` | Proxied |
| CNAME | `api.army` | `army-api.osc-fr1.scalingo.io` | Proxied |

The `ai.army` record is managed by the Worker's Custom Domain and must not be replaced with a manual CNAME.

TLS and caching:

1. Set Cloudflare SSL/TLS mode to **Full (strict)**.
2. Keep Cloudflare **Always Use HTTPS** off for these Scalingo hostnames because Scalingo needs the plaintext `/.well-known/` path for Let's Encrypt renewal.
3. Enable Scalingo Force HTTPS after certificates are active:

```powershell
scalingo --app army-web force-https --enable
scalingo --app army-api force-https --enable
```

4. Do not create a “Cache Everything” rule for either hostname.
5. Bypass cache for `api.army.lengrowth.com/*`, all authenticated responses, and dashboard HTML. Cloudflare may cache immutable `/_next/static/*` assets using their origin cache headers.
6. Add a conservative rate-limit rule for login/register and obvious abusive API traffic only after observing normal dashboard polling. The dashboard polls some endpoints every 2–10 seconds, so a blanket low API limit will break it.

Cutover checks:

```powershell
Resolve-DnsName army.lengrowth.com
Resolve-DnsName api.army.lengrowth.com
Resolve-DnsName ai.army.lengrowth.com
Invoke-WebRequest https://army.lengrowth.com -Method Head
Invoke-RestMethod https://api.army.lengrowth.com/health
Invoke-RestMethod https://ai.army.lengrowth.com/health
```

Use a browser to verify login, dashboard navigation, task list, task creation without execution, approvals, and logout. Confirm browser network requests go only to `https://api.army.lengrowth.com` and there are no CORS or mixed-content errors.

Gate 4: all three TLS certificates are valid; browser and API smoke tests pass through Cloudflare; no sensitive response is cached; origin logs receive expected traffic.

## 10. Phase 5 — connect and validate the Windows poller

Update the local poller's untracked `.env` without printing it:

```text
API_URL=https://api.army.lengrowth.com
LLM_PROVIDER=cloudflare
CLOUDFLARE_AI_BASE_URL=https://ai.army.lengrowth.com/v1
CLOUDFLARE_AI_MODEL=@cf/deepseek-ai/deepseek-v4-pro-0813
CLOUDFLARE_AI_GATEWAY_TOKEN=<from password manager>
LLM_AUTO_FALLBACK=true
```

Keep `AGENT_TOKEN`, `HMAC_KEY`, identity, and path values unchanged. Restart the poller and verify:

1. Heartbeat is accepted by the production API.
2. The local worker appears online in the dashboard.
3. A harmless test task is leased once, renewed, completed once, and produces one result.
4. A small LLM-backed task reports Cloudflare/DeepSeek as the active provider.
5. No token or prompt content appears in local, Worker, or Scalingo logs.

Gate 5: one complete browser -> API -> local poller -> Workers AI -> API -> browser round trip succeeds.

## 11. Phase 6 — canary, monitoring, and cleanup

For the first 24 hours:

- Keep one API web container.
- Keep the old provider credentials for emergency fallback.
- Monitor Scalingo API/dashboard logs, Worker observability, Workers AI spend, Atlas connections, task retries, JSON parse failures, and latency.
- Test scheduled work once with Telegram still disabled; then enable Telegram and verify exactly one bot/scheduler instance.
- Compare a fixed prompt set across the former main model and DeepSeek for valid JSON, routing decisions, safety behavior, and output quality.
- Set a Cloudflare billing alert/limit appropriate to expected use.

After a stable canary:

- Decide whether `LLM_AUTO_FALLBACK` remains enabled.
- Remove unused chat-provider credentials only if embeddings do not depend on them.
- Keep `OPENAI_API_KEY` while `EMBEDDING_PROVIDER=openai`.
- Enable Scalingo automatic deployments from protected `main` only after CI runs API tests, local tests, dashboard lint/build, Worker tests/typecheck, and Wrangler dry run.

## 12. Rollback plan

### AI-only rollback

Fastest safe rollback:

1. Set `LLM_PROVIDER=gemini` or `openai` in `army-api` and the local poller's `.env`.
2. Restart `army-api` and the local poller.
3. Confirm a fixed smoke prompt succeeds.
4. Leave the Worker deployed for diagnosis; do not delete it during an incident.

If only the Worker release is bad:

```powershell
Set-Location cloudflare/army-ai
npx wrangler versions list
npx wrangler rollback
```

### Scalingo application rollback

Use Scalingo's previous successful deployment or revert the offending Git commit and manually deploy `main`. Do not force-push or reset the user's repository.

### DNS rollback

Restore the prior CNAME targets recorded immediately before Phase 4. Do not delete DNS records without recording their previous values. Because records are proxied, verify recovery with HTTPS requests rather than relying only on DNS output.

### Data rollback

This plan performs no database migration. Do not drop collections or Atlas indexes. If application writes are incompatible, stop task creation, revert the API release, and inspect affected documents before any repair.

## 13. Definition of done

The deployment is complete only when all are true:

- `https://army.lengrowth.com` serves the dashboard with valid TLS.
- `https://api.army.lengrowth.com/health` returns healthy through Cloudflare.
- `https://ai.army.lengrowth.com/health` returns healthy, while unauthenticated inference returns `401`.
- Both Scalingo apps deploy reproducibly from a fresh Git checkout using `PROJECT_DIR`.
- Dashboard `src/lib` files and `.env.example` are tracked.
- API, local, dashboard, and Worker test/build gates pass.
- Cloud and local chat clients use Workers AI DeepSeek V4 Pro as primary.
- Embeddings still use the existing OpenAI model and Atlas index.
- One end-to-end local-agent task completes exactly once.
- CORS is restricted, secrets are absent from Git/logs, and API responses are not cached.
- Rollback has been rehearsed with a smoke test.
- Final resource IDs, Scalingo default URLs, custom domains, environment-variable names, deployment commit, and rollback version are recorded without secret values.

## 14. Later improvements, not part of this deployment

- Move the in-process scheduler and Telegram bot to a dedicated Scalingo process with a MongoDB-backed distributed lease, then permit horizontal API scaling.
- Migrate embeddings to a Workers AI embedding model using a new Atlas vector index, side-by-side re-ingestion, quality evaluation, and atomic index switch.
- Move browser auth from `localStorage` to secure HttpOnly cookies after a separate CSRF/session design review.
- Add staging hostnames/apps and promotion-based releases if deployment frequency grows.
- Add Cloudflare Access or service-token authentication for private administrative surfaces if the dashboard is not intended for the public Internet.

## 15. Current references

- [Scalingo monorepo deployment with `PROJECT_DIR`](https://doc.scalingo.com/platform/app/monorepo)
- [Scalingo + Cloudflare custom-domain configuration](https://doc.scalingo.com/platform/app/cloudflare-scalingo-app)
- [Scalingo Procfile rules](https://doc.scalingo.com/platform/app/procfile)
- [Scalingo Python runtime selection](https://doc.scalingo.com/languages/python/start)
- [Scalingo Node.js and Next.js startup](https://doc.scalingo.com/languages/nodejs/start)
- [Scalingo regional egress addresses](https://doc.scalingo.com/platform/networking/public/egress)
- [Cloudflare Workers AI DeepSeek V4 Pro model](https://developers.cloudflare.com/workers-ai/models/deepseek-v4-pro-0813/)
- [Cloudflare Workers AI OpenAI-compatible API](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)
- [Cloudflare Worker Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)
- [Cloudflare Workers best practices](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/)
