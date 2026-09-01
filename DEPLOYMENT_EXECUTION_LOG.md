# Deployment execution log

## 2026-09-01

### Phase 0 — repository readiness

- Pre-existing user change preserved: `DEPLOYMENT_PLAN_SCALINGO_CLOUDFLARE.md` was untracked at start.
- Dashboard ignore blockers repaired; `src/lib/api.ts`, `src/lib/utils.ts`, and `dashboard/.env.example` are staged for tracking.
- Added API `.python-version`, `Procfile`, direct pinned `pytz`, configurable CORS, and separate embedding-provider configuration.
- API tests: 293 passed.
- Local tests: 264 passed.
- Dashboard lint: passed with 0 errors and legacy warnings.
- Dashboard production build: passed.
- `git diff --check`: passed.

### Phase 1 — Worker gateway local gate

- Worker project: `cloudflare/army-ai`.
- Wrangler: 4.127.1.
- Current Cloudflare docs consulted for Workers best practices, Workers AI DeepSeek V4 Pro, custom domains, Wrangler configuration, observability, and Vitest integration.
- Current Vitest integration uses `@cloudflare/vitest-plugin` because it supersedes the older `@cloudflare/vitest-pool-workers` package.
- Generated runtime types include the Workers AI binding and required gateway secret declaration.
- Worker tests: 5 passed.
- TypeScript, generated-type check, Wrangler dry-run, and startup analysis: passed.
- Worker versions: none yet; `army-ai` does not exist on the account at inspection time.
- Public DNS inspection: all three requested hostnames currently resolve through Cloudflare; prior record values were not changed.

### Blockers before external mutation

- The shared AI gateway secret is not available in an approved password manager/secret store, so the Worker cannot be securely deployed or propagated to Scalingo and the local poller.
- Workers AI DeepSeek V4 Pro requires Workers Paid or prepaid AI Gateway credits; account entitlement has not been verified.
- Existing public DNS records for `army.lengrowth.com`, `api.army.lengrowth.com`, and `ai.army.lengrowth.com` must be inspected in the Cloudflare account before cutover; no DNS changes were made.
- Scalingo CLI is authenticated at 1.47.0 and requests an update to 1.48.0 before resource mutation.
