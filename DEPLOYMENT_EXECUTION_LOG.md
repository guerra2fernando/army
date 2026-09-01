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

### Post-gate deployment evidence

- User confirmed Workers Paid and the Lengrowth Cloudflare account; a newly generated random gateway token was provisioned to Worker `army-ai`, Scalingo `army-api`, and the Windows user environment without printing its value.
- Worker deployment succeeded as version `3cb7aafa-6b4b-4ce9-9928-6552269585ff`.
- Scalingo `army-web` deployment succeeded from commit `4301210e0c4de6a3dbbd277c34517241514d3b15`; one web container is running.
- Scalingo `army-api` deployments failed with `BSR-032` during source fetch across GitHub integration, Scalingo Git, local archive, and GitHub archive URL attempts. No API container is running.
- Retried with official Scalingo CLI `1.48.0`; `BSR-032` persisted before buildpack execution, ruling out the installed CLI version.
- Recreated `army-api` in the same project/region and retried with the fresh app ID `6a970d4122c0096bc4d223e0`; `BSR-032` persisted. A temporary `army-api-recovery` app was also tested and removed after the same failure. `army-web` remains running.
- `PROJECT_DIR=armlenquant-cloud/api` and `BUILDPACK_NAME=python` are configured on `army-api`; API secrets are present by name but no values are recorded here.
- Explicit `web:1` provisioning was attempted; no container could start because the deployment never produced an image.
- After setting `BUILDPACK_NAME=python`, the linked GitHub manual deployment still failed at source fetch/buildpack handoff with `BSR-032`: deployment `860616d4-25fe-48ff-887b-c2427c7ab9d4`, commit `2ad277c95fd199037911162ced5394f5083ff418`, image size `0 B`. This rules out the Python web command and buildpack auto-detection as the cause.
