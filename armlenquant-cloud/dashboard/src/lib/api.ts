import axios, { AxiosInstance, AxiosError } from "axios";
import type {
  APIResponse,
  AuthResponse,
  LoginCredentials,
  RegisterData,
  User,
  Task,
  CreateTaskData,
  Agent,
  SystemHealth,
  CryptoMarketOverview,
  CryptoBrief,
  CryptoSignal,
  CryptoAnalysis,
  UserSettings,
  NotificationListResponse,
  TelegramStatus,
  NotificationType,
  NotificationPriority,
  Workflow,
  ReviewQueueItem,
  SendIntent,
  FollowupPlan,
  DraftMessage,
  FollowupDraft,
  AgentConfigVersion,
  AgentConfigTestResult,
  SafetyStatus,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

class APIClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        "Content-Type": "application/json",
      },
    });

    // Add auth interceptor
    this.client.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });

    // Handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.clearToken();
          if (typeof window !== "undefined") {
            window.location.href = "/login";
          }
        }
        return Promise.reject(error);
      }
    );

    // Load token from storage
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("token");
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
  }

  getToken(): string | null {
    return this.token;
  }

  async get<T = unknown>(url: string, config?: { params?: Record<string, unknown> }): Promise<{ data: T }> {
    const response = await this.client.get<T>(url, config);
    return { data: response.data };
  }

  async post<T = unknown>(url: string, data?: unknown, config?: { params?: Record<string, unknown> }): Promise<{ data: T }> {
    const response = await this.client.post<T>(url, data, config);
    return { data: response.data };
  }

  async put<T = unknown>(url: string, data?: unknown, config?: { params?: Record<string, unknown> }): Promise<{ data: T }> {
    const response = await this.client.put<T>(url, data, config);
    return { data: response.data };
  }

  async patch<T = unknown>(url: string, data?: unknown, config?: { params?: Record<string, unknown> }): Promise<{ data: T }> {
    const response = await this.client.patch<T>(url, data, config);
    return { data: response.data };
  }

  // =========================================================================
  // Auth
  // =========================================================================

  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await this.client.post<AuthResponse>(
      "/api/v1/auth/login",
      credentials
    );
    this.setToken(response.data.access_token);
    return response.data;
  }

  async register(data: RegisterData): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(
      "/api/v1/auth/register",
      data
    );
    return response.data;
  }

  async getMe(): Promise<User> {
    const response = await this.client.get<User>("/api/v1/auth/me");
    return response.data;
  }

  logout() {
    this.clearToken();
  }

  // =========================================================================
  // Tasks
  // =========================================================================

  async createTask(data: CreateTaskData): Promise<Task> {
    const response = await this.client.post<Task>("/api/v1/tasks", data);
    return response.data;
  }

  async getTasks(params?: {
    status?: string;
    agent_target?: string;
    limit?: number;
  }): Promise<Task[]> {
    const response = await this.client.get<Task[]>("/api/v1/tasks", { params });
    return response.data;
  }

  async getTask(taskId: string): Promise<Task> {
    const response = await this.client.get<Task>(`/api/v1/tasks/${taskId}`);
    return response.data;
  }

  async deleteTask(taskId: string): Promise<APIResponse> {
    const response = await this.client.delete<APIResponse>(`/api/v1/tasks/${taskId}`);
    return response.data;
  }

  async getTaskDetails(taskId: string): Promise<any> {
    const response = await this.client.get<any>(`/api/v1/tasks/${taskId}/details`);
    return response.data;
  }

  async recoverLeases(): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(`/api/v1/tasks/recover_leases`);
    return response.data;
  }

  // =========================================================================
  // Workflows
  // =========================================================================

  async listWorkflows(params?: { status?: string; limit?: number }): Promise<Workflow[]> {
    const response = await this.client.get<Workflow[]>("/api/v1/workflows", { params });
    return response.data;
  }

  async getWorkflow(workflowId: string): Promise<Workflow> {
    const response = await this.client.get<Workflow>(`/api/v1/workflows/${workflowId}`);
    return response.data;
  }

  async updateWorkflowStatus(workflowId: string, status: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(
      `/api/v1/workflows/${workflowId}/status`,
      { status }
    );
    return response.data;
  }

  async approveWorkflow(workflowId: string, token?: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(`/api/v1/workflows/${workflowId}/approve`, null, {
      params: token ? { token } : undefined,
    });
    return response.data;
  }

  async rejectWorkflow(workflowId: string, reason?: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(`/api/v1/workflows/${workflowId}/reject`, {
      reason,
    });
    return response.data;
  }

  async resumeWorkflow(workflowId: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(`/api/v1/workflows/${workflowId}/resume`);
    return response.data;
  }

  // =========================================================================
  // Commercial Ops
  // =========================================================================

  async listReviewItems(params?: {
    status?: string;
    lane?: string;
    target_persona?: string;
    recommended_channel?: string;
    review_kind?: string;
    profile_slug?: string;
    business_slug?: string;
    company?: string;
    limit?: number;
  }): Promise<ReviewQueueItem[]> {
    const response = await this.client.get<ReviewQueueItem[]>("/api/v1/commercial/review-items", { params });
    return response.data;
  }

  async getReviewItem(reviewId: string): Promise<ReviewQueueItem> {
    const response = await this.client.get<ReviewQueueItem>(`/api/v1/commercial/review-items/${reviewId}`);
    return response.data;
  }

  async approveReviewItem(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/approve`, { note });
    return response.data;
  }

  async rejectReviewItem(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/reject`, { note });
    return response.data;
  }

  async archiveReviewItem(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/archive`, { note });
    return response.data;
  }

  async pauseReviewFollowup(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/pause-followup`, { note });
    return response.data;
  }

  async resumeReviewFollowup(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/resume-followup`, { note });
    return response.data;
  }

  async cancelReviewFollowup(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/cancel-followup`, { note });
    return response.data;
  }

  async markReviewReplied(reviewId: string, note?: string): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/mark-replied`, { note });
    return response.data;
  }

  async rerouteReviewItem(reviewId: string, payload: {
    note?: string;
    lane?: string;
    specialist?: string;
    target_persona?: string;
    recommended_channel?: string;
  }): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/reroute`, payload);
    return response.data;
  }

  async editReviewItem(reviewId: string, payload: {
    note?: string;
    updated_draft?: DraftMessage;
    updated_followups?: FollowupDraft[];
  }): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(`/api/v1/commercial/review-items/${reviewId}/edit`, payload);
    return response.data;
  }

  async listSendIntents(limit = 100): Promise<SendIntent[]> {
    const response = await this.client.get<SendIntent[]>("/api/v1/commercial/send-intents", { params: { limit } });
    return response.data;
  }

  async listFollowupPlans(limit = 100): Promise<FollowupPlan[]> {
    const response = await this.client.get<FollowupPlan[]>("/api/v1/commercial/followups", { params: { limit } });
    return response.data;
  }

  async dispatchSendIntent(sendIntentId: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(`/api/v1/commercial/send-intents/${sendIntentId}/dispatch`);
    return response.data;
  }

  // =========================================================================
  // Agents
  // =========================================================================

  async getAgents(): Promise<Agent[]> {
    const response = await this.client.get<Agent[]>("/api/v1/agents");
    return response.data;
  }

  async updateAgentStatus(
    agentName: string,
    status: string
  ): Promise<APIResponse> {
    const response = await this.client.patch<APIResponse>(
      `/api/v1/agents/${agentName}/status`,
      null,
      { params: { status } }
    );
    return response.data;
  }

  // =========================================================================
  // Health
  // =========================================================================

  async getHealth(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }

  async getDetailedHealth(): Promise<APIResponse<SystemHealth>> {
    const response = await this.client.get<APIResponse<SystemHealth>>(
      "/api/v1/health/detailed"
    );
    return response.data;
  }

  // =========================================================================
  // Crypto
  // =========================================================================

  async getCryptoMarket(): Promise<CryptoMarketOverview> {
    const response = await this.client.get<CryptoMarketOverview>(
      "/api/v1/crypto/market"
    );
    return response.data;
  }

  async getCryptoBrief(date?: string): Promise<CryptoBrief> {
    const response = await this.client.get<CryptoBrief>("/api/v1/crypto/brief", {
      params: date ? { date } : undefined,
    });
    return response.data;
  }

  async generateCryptoBrief(): Promise<CryptoBrief> {
    const response = await this.client.post<CryptoBrief>(
      "/api/v1/crypto/brief/generate"
    );
    return response.data;
  }

  async getCryptoSignals(): Promise<{ signals: CryptoSignal[] }> {
    const response = await this.client.get<{ signals: CryptoSignal[] }>(
      "/api/v1/crypto/signals"
    );
    return response.data;
  }

  async analyzeCrypto(symbol: string): Promise<CryptoAnalysis> {
    const response = await this.client.get<CryptoAnalysis>(
      `/api/v1/crypto/analyze/${symbol}`
    );
    return response.data;
  }

  // =========================================================================
  // Settings
  // =========================================================================

  async getUserSettings(): Promise<UserSettings> {
    try {
      const response = await this.client.get<UserSettings>(
        "/api/v1/users/settings"
      );
      return response.data;
    } catch {
      // Return default settings if endpoint doesn't exist yet
      return {
        notifications_enabled: true,
        email_notifications: true,
        telegram_notifications: false,
        theme: "dark",
      };
    }
  }

  async updateUserSettings(settings: Partial<UserSettings>): Promise<UserSettings> {
    const response = await this.client.patch<UserSettings>(
      "/api/v1/users/settings",
      settings
    );
    return response.data;
  }

  // =========================================================================
  // Notifications
  // =========================================================================

  async getNotifications(params?: {
    limit?: number;
    type?: NotificationType;
  }): Promise<NotificationListResponse> {
    const response = await this.client.get<NotificationListResponse>(
      "/api/v1/notifications/recent",
      { params }
    );
    return response.data;
  }

  async sendNotification(data: {
    title: string;
    message: string;
    type?: NotificationType;
    priority?: NotificationPriority;
  }): Promise<{ success: boolean; notification_id: string }> {
    const response = await this.client.post("/api/v1/notifications/send", data);
    return response.data;
  }

  async modifyPlan(taskId: string, planId: string, modifications: any): Promise<APIResponse> {
    const response = await this.client.put<APIResponse>(
      `/api/v1/tasks/${taskId}/plans/${planId}/modify`,
      modifications
    );
    return response.data;
  }

  async getTelegramStatus(): Promise<TelegramStatus> {
    const response = await this.client.get<TelegramStatus>(
      "/api/v1/notifications/telegram/status"
    );
    return response.data;
  }

  async testTelegramNotification(): Promise<{ success: boolean; message: string }> {
    const response = await this.client.post("/api/v1/notifications/telegram/test");
    return response.data;
  }

  // =========================================================================
  // Agent Configs
  // =========================================================================

  async getAgentConfigVersions(agentId: string): Promise<AgentConfigVersion[]> {
    const response = await this.client.get<AgentConfigVersion[]>(
      `/api/v1/agents/${agentId}/config/versions`
    );
    return response.data;
  }

  async rollbackAgentConfig(agentId: string, targetVersion: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>(
      `/api/v1/agents/${agentId}/config/rollback`,
      null,
      { params: { target_version: targetVersion } }
    );
    return response.data;
  }

  async testAgentConfig(agentId: string, payload: Partial<AgentConfigVersion>): Promise<AgentConfigTestResult> {
    const response = await this.client.post<AgentConfigTestResult>(
      `/api/v1/agents/${agentId}/config/test`,
      payload
    );
    return response.data;
  }

  // =========================================================================
  // Safety / Security
  // =========================================================================

  async getSafetyStatus(): Promise<SafetyStatus> {
    const response = await this.client.get<SafetyStatus>("/api/v1/safety/status");
    return response.data;
  }

  async activateKillSwitch(reason: string): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>("/api/v1/safety/kill-switch", { reason });
    return response.data;
  }

  async resetKillSwitch(): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>("/api/v1/safety/kill-switch/reset");
    return response.data;
  }

  async upsertSpawnBudget(payload: {
    budget_id?: string;
    scope_type: string;
    agent_type_filter?: string | null;
    max_spawns: number;
    time_window?: string;
    action_on_exceed?: string;
    cooldown_minutes?: number;
  }): Promise<APIResponse> {
    const response = await this.client.post<APIResponse>("/api/v1/safety/spawn-budgets", payload);
    return response.data;
  }
}

export const api = new APIClient();
