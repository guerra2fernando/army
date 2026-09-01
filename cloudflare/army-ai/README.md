# army-ai

Authenticated OpenAI-compatible gateway for Workers AI DeepSeek V4 Pro.

The gateway pins `@cf/deepseek-ai/deepseek-v4-pro-0813` server-side, accepts bounded synchronous chat requests, and never logs request bodies, prompts, completions, or authorization headers. Set `CLOUDFLARE_AI_GATEWAY_TOKEN` with `npx wrangler secret put` before deployment.
