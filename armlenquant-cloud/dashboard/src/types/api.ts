// API Response types
export interface APIResponse<T = unknown> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}

// User types
export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Task types
export type TaskStatus =
  | "PENDING"
  | "PLANNING"          // New: Analyzing and planning phase
  | "PLAN_READY"        // New: Master plan ready for approval
  | "APPROVED"          // New: Human approved the plan
  | "PICKED_UP"
  | "EXECUTING"         // New: Currently executing phases
  | "PHASE_READY"       // New: Phase completed, ready for next
  | "PHASE_REVIEW"      // New: Phase ready for human review
  | "IN_PROGRESS"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type AgentTarget =
  | "ORCHESTRATOR"
  | "CRYPTO_SENTINEL"
  | "JOB_HUNTER"
  | "COMMERCIAL_SCOUT"
  | "OUTREACH_EXECUTOR"
  | "IDEAS_MACHINE"
  | "META_BUILDER";

export interface Task {
  task_id: string;
  idempotency_key?: string;
  agent_target: AgentTarget;
  title: string;
  status: TaskStatus;
  priority: number;
  created_at: string;
  updated_at?: string;
  worker_id?: string | null;
  picked_up_by?: string | null;
  lease_until?: string | null;
  picked_up_at?: string | null;
  last_execution_started?: string | null;
  execution_count?: number;
  payload?: Record<string, unknown>;
  error_log?: string[];
  completed_at?: string;
  result?: Record<string, unknown> | string;
  recurring?: boolean;
}

// Workflow types
export type WorkflowStatus =
  | "PENDING"
  | "RUNNING"
  | "PAUSED"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export type WorkflowStepStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export type ApprovalState = "PENDING" | "APPROVED" | "REJECTED";

export interface WorkflowStep {
  step_id: string;
  name: string;
  agent_target: string;
  status: WorkflowStepStatus;
  task_id?: string | null;
  inputs?: Record<string, unknown>;
  outputs?: Record<string, unknown> | null;
  started_at?: string | null;
  completed_at?: string | null;
  error?: string | null;
  worker_id?: string | null;
  approval_required?: boolean;
  approval_state?: ApprovalState | null;
  approval_context?: Record<string, unknown>;
  approved_by?: string | null;
}

export interface Workflow {
  workflow_id: string;
  type: string;
  status: WorkflowStatus;
  current_step: number;
  steps: WorkflowStep[];
  approval_required: boolean;
  approved_by?: string | null;
  approval_state?: ApprovalState;
  approval_token?: string | null;
  approval_config?: Record<string, unknown>;
  approval_requested_at?: string | null;
  approval_reason?: string | null;
  approved_at?: string | null;
  resume_token?: Record<string, unknown> | null;
  created_by: string;
  priority: number;
  related_tasks?: string[];
  parent_workflow?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export type ReviewQueueStatus =
  | "PENDING"
  | "APPROVED"
  | "BLOCKED"
  | "REJECTED"
  | "REROUTED"
  | "ARCHIVED"
  | "PAUSED";

export type ReviewItemKind = "INITIAL" | "FOLLOWUP";

export type OutreachChannel = "EMAIL" | "LINKEDIN_CONNECT" | "LINKEDIN_DM" | "MANUAL";

export interface DraftMessage {
  channel: OutreachChannel;
  subject?: string | null;
  body: string;
  cta?: string;
}

export interface FollowupDraft {
  delay_days: number;
  channel: OutreachChannel;
  body: string;
}

export interface ReviewQueueItem {
  review_id: string;
  review_kind?: ReviewItemKind;
  parent_review_id?: string | null;
  followup_plan_id?: string | null;
  followup_step?: number | null;
  opportunity_id?: string | null;
  route_id?: string | null;
  source_url: string;
  kind: "JOB" | "COMMERCIAL";
  lane: string;
  specialist: string;
  target_persona: string;
  status: ReviewQueueStatus;
  confidence: number;
  profile_binding: Record<string, unknown>;
  recommended_channel: OutreachChannel;
  rationale: string[];
  recommended_next_step: string;
  primary_draft: DraftMessage;
  followups: FollowupDraft[];
  draft_metadata?: Record<string, unknown>;
  paused_followup?: boolean;
  blocked_reasons?: string[];
  send_intent_id?: string | null;
  followup_status?: FollowupStatus | null;
  next_action_at?: string | null;
  latest_note?: string | null;
  history?: Array<Record<string, unknown>>;
  created_at?: string;
  updated_at?: string;
}

export type SendIntentStatus = "READY" | "DISPATCHED" | "SENT" | "MANUAL" | "FAILED" | "CANCELLED";

export type FollowupStatus =
  | "SCHEDULED"
  | "PENDING_REVIEW"
  | "PAUSED"
  | "CANCELLED"
  | "SUPPRESSED"
  | "COMPLETED";

export interface SendIntent {
  send_intent_id: string;
  review_id: string;
  opportunity_id?: string | null;
  status: SendIntentStatus;
  channel: OutreachChannel;
  profile_binding: Record<string, unknown>;
  idempotency_key: string;
  cooldown_key: string;
  provider: string;
  blocked_reasons?: string[];
  followup_plan_id?: string | null;
  followup_step?: number | null;
  is_followup?: boolean;
  dispatch_task_id?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  dispatched_at?: string | null;
  completed_at?: string | null;
  retry_count?: number;
  max_retries?: number;
  last_error?: string | null;
  payload?: Record<string, unknown>;
}

export interface FollowupPlan {
  followup_id: string;
  review_id: string;
  root_review_id?: string | null;
  opportunity_id?: string | null;
  status: FollowupStatus;
  current_step?: number;
  next_action_at?: string | null;
  last_sent_at?: string | null;
  last_review_id?: string | null;
  reply_detected_at?: string | null;
  suppression_reason?: string | null;
  cancelled_reason?: string | null;
  paused_reason?: string | null;
  drafts: FollowupDraft[];
  profile_binding: Record<string, unknown>;
  updated_at?: string;
}

export interface CreateTaskData {
  agent_target: AgentTarget;
  payload: Record<string, unknown>;
  priority?: number;
  recurring?: boolean;
}

// Agent types
export type AgentStatus = "ACTIVE" | "PAUSED" | "FAILED" | "INITIALIZING";

export interface AgentPerformance {
  success_rate: number;
  total_runs: number;
  failed_runs: number;
  avg_execution_time_ms: number;
  last_run_at?: string;
  last_error?: string;
}

export interface Agent {
  agent_id: string;
  agent_name: string;
  version: string;
  location: "CLOUD" | "LOCAL";
  status: AgentStatus;
  trigger_type: string;
  performance: AgentPerformance;
  created_at: string;
  config_version?: string;
  granted_capabilities?: CapabilityGrant[];
  capability_usage?: Record<string, CapabilityUsage>;
}

export interface CapabilityGrant {
  capability_id: string;
  granted_at?: string;
  granted_by?: string;
  limits_override?: Record<string, unknown>;
  conditions?: string[];
  policy_override?: Record<string, unknown>;
}

export interface CapabilityUsage {
  today_count?: number;
  total_count?: number;
  last_used?: string;
  quota_remaining?: number;
}

export interface AgentConfigVersion {
  version: string;
  prompt_template?: string;
  config_params?: Record<string, unknown>;
  schema_version?: string;
  created_at?: string;
  created_by?: string;
  performance_baseline?: Record<string, unknown>;
  is_active?: boolean;
  notes?: string;
}

export interface AgentConfigTestResult {
  safe: boolean;
  message: string;
  details?: Record<string, unknown>;
}

// Health types
export interface SystemHealth {
  status: string;
  timestamp: string;
  database: string;
  agents: {
    total: number;
    active: number;
  };
  task_queue: {
    pending: number;
    in_progress: number;
  };
}

// Crypto types
export interface CryptoGlobal {
  total_market_cap: number;
  total_volume_24h: number;
  btc_dominance: number;
  active_cryptocurrencies: number;
  market_cap_change_24h: number;
}

export interface CryptoCoin {
  id: string;
  symbol: string;
  name: string;
  current_price: number;
  market_cap: number;
  market_cap_rank: number;
  price_change_percentage_24h: number;
  price_change_percentage_7d: number;
  total_volume: number;
  high_24h: number;
  low_24h: number;
  image?: string;
}

export interface CryptoMarketOverview {
  global: CryptoGlobal;
  top_coins: CryptoCoin[];
}

export type SignalType = "BUY" | "SELL" | "HOLD";

export interface CryptoSignal {
  signal_id: string;
  symbol: string;
  signal_type: SignalType;
  confidence: number;
  entry_price: number;
  target_price?: number;
  stop_loss?: number;
  reasoning: string | Record<string, unknown>;
  created_at: string;
  expires_at?: string;
  status: "ACTIVE" | "EXPIRED" | "TRIGGERED";
}

export interface TechnicalIndicators {
  rsi: number;
  macd: {
    macd: number;
    signal: number;
    histogram: number;
  };
  sma_20: number;
  sma_50: number;
  bollinger: {
    upper: number;
    middle: number;
    lower: number;
  };
}

export interface CryptoAnalysis {
  symbol: string;
  price: number;
  indicators: TechnicalIndicators;
  sentiment: "BULLISH" | "BEARISH" | "NEUTRAL";
  signal: CryptoSignal | null;
  summary: string;
}

export interface CryptoBrief {
  date: string;
  market_sentiment: "BULLISH" | "BEARISH" | "NEUTRAL";
  summary: string;
  top_movers: {
    coin: string;
    change: number;
    signal?: SignalType;
  }[];
  signals: CryptoSignal[];
  news_highlights: string[];
  created_at: string;
}

// User Settings types
export interface UserSettings {
  notifications_enabled: boolean;
  email_notifications: boolean;
  telegram_notifications: boolean;
  telegram_chat_id?: string;
  theme: "dark" | "light" | "system";
  default_job_locations?: string[];
  default_job_titles?: string[];
  crypto_watchlist?: string[];
}

// Notification types
export type NotificationType =
  | "task_completed"
  | "task_failed"
  | "agent_alert"
  | "system_error"
  | "crypto_signal"
  | "job_match"
  | "daily_brief"
  | "custom";

export type NotificationPriority = "low" | "normal" | "high" | "urgent";

export interface Notification {
  notification_id: string;
  type: NotificationType;
  title: string;
  message: string;
  priority: NotificationPriority;
  delivered: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  success: boolean;
  notifications: Notification[];
  count: number;
}

export interface TelegramStatus {
  enabled: boolean;
  connected: boolean;
  chat_id_configured: boolean;
}

// Safety / security types
export interface SpawnBudget {
  budget_id: string;
  scope_type: string;
  agent_type_filter?: string | null;
  max_spawns: number;
  current_spawns?: number;
  time_window?: string;
  action_on_exceed?: string;
  cooldown_minutes?: number;
  window_start?: string;
  violations?: Array<Record<string, unknown>>;
}

export interface SafetyStatus {
  kill_switch_active: boolean;
  orchestrator_enabled: boolean;
  budgets: SpawnBudget[];
}

