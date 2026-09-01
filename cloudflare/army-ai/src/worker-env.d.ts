interface Env {
  /** Set with `wrangler secret put`; absent until the first secret provisioning step. */
  CLOUDFLARE_AI_GATEWAY_TOKEN?: string;
}
