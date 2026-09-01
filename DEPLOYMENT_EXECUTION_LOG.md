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
- Generated runtime types include the Workers AI binding; the gateway secret is provisioned separately at runtime.
- Worker tests: 5 passed.
- TypeScript, generated-type check, Wrangler dry-run, and startup analysis: passed.
- Worker deployed: `army-ai`, version `3cb7aafa-6b4b-4ce9-9928-6552269585ff`, custom domain `ai.army.lengrowth.com`.
- Public DNS inspection: all three requested hostnames currently resolve through Cloudflare; prior record values were not changed.

### Scalingo resources created

- Project: `army` (`prj-f6317a10-7ecd-4180-a982-03d1d8e96809`).
- Applications: `army-api`, `army-web`.
- Region: `osc-fr1`.
- GitHub integration: `https://github.com/guerra2fernando/army`, branch `main`, auto-deploy disabled.
- Expected default origins: `army-api.osc-fr1.scalingo.io`, `army-web.osc-fr1.scalingo.io`.
- Both apps remain un-deployed with one desired web process pending first verified boot.

### Remaining activation blockers

- The shared AI gateway secret is not yet provisioned. The Worker is deployed fail-closed, but authenticated inference and propagation to Scalingo/local poller require secure entry.
- User confirmed Workers Paid is active for the Lengrowth Cloudflare account.
- Existing public DNS records for `army.lengrowth.com`, `api.army.lengrowth.com`, and `ai.army.lengrowth.com` must be inspected in the Cloudflare account before cutover; no DNS changes were made.
- Scalingo CLI is authenticated at 1.47.0 and requests an update to 1.48.0 for future CLI-sensitive mutations.
- Scalingo secret values are not yet configured because secure entry requires the user’s approved secret store/dashboard workflow.
- Initial HTTPS probes from Windows PowerShell/curl failed during local Schannel TLS negotiation; the custom-domain deployment itself completed successfully.
