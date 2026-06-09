"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  PlayCircle,
  Calendar,
  User,
  Zap,
  TrendingUp,
  BarChart3,
  History,
  ExternalLink,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { formatDateInTbilisi, formatDistanceToNowInTbilisi } from "@/lib/utils";

interface TaskDetails {
  task: any;
  execution_metrics: {
    execution_time_seconds: number | null;
    retry_count: number;
    error_count: number;
    has_result: boolean;
  };
  history: {
    events: Array<{
      event_type: string;
      timestamp: string;
      details: any;
    }>;
    total_events: number;
  };
  agent_specific: any;
  comparison: {
    similar_tasks_count: number;
    similar_tasks: any[];
  };
  metadata: {
    created_by_user: boolean;
    has_worker: boolean;
    is_recurring: boolean;
    priority_level: string;
  };
}

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.taskId as string;

  const { data: taskDetails, isLoading, error, refetch } = useQuery({
    queryKey: ["task-details", taskId],
    queryFn: async () => {
      try {
        return await api.getTaskDetails(taskId);
      } catch (e) {
        // Fallback to basic task info if details endpoint fails
        const task = await api.getTask(taskId);
        return {
          task,
          execution_metrics: {
            execution_time_seconds: null,
            retry_count: 0,
            error_count: task.error_log?.length || 0,
            has_result: task.result !== null,
          },
          history: {
            events: [],
            total_events: 0,
          },
          agent_specific: null,
          comparison: {
            similar_tasks_count: 0,
            similar_tasks: [],
          },
          metadata: {
            created_by_user: true,
            has_worker: task.worker_id !== null,
            is_recurring: false,
            priority_level: task.priority >= 8 ? "high" : task.priority >= 5 ? "normal" : "low",
          },
        } as TaskDetails;
      }
    },
    enabled: !!taskId,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Tasks
          </Button>
        </div>
        <div className="text-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin mx-auto text-zinc-500" />
          <p className="text-zinc-400 mt-4">Loading task details...</p>
        </div>
      </div>
    );
  }

  if (error || !taskDetails) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Tasks
          </Button>
        </div>
        <div className="text-center py-12">
          <AlertCircle className="w-8 h-8 mx-auto text-red-500" />
          <p className="text-zinc-400 mt-4">Failed to load task details</p>
          <Button variant="outline" className="mt-4" onClick={() => refetch()}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const { task, execution_metrics, history, agent_specific, comparison, metadata } = taskDetails;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "FAILED":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "IN_PROGRESS":
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
      case "PENDING":
        return <Clock className="w-5 h-5 text-yellow-500" />;
      default:
        return <PlayCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "FAILED":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      case "IN_PROGRESS":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "PENDING":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      default:
        return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    }
  };

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return "N/A";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${Math.round(seconds / 3600)}h`;
  };

  const formatObject = (obj: any): string => {
    if (!obj) return "None";
    if (typeof obj === "string") return obj;
    try {
      return JSON.stringify(obj, null, 2);
    } catch {
      return String(obj);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Tasks
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white">{task.title || "Task Details"}</h1>
            <p className="text-zinc-400">Task ID: {task.task_id}</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Status Overview */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            {getStatusIcon(task.status)}
            Task Overview
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Status</p>
              <Badge variant="outline" className={getStatusColor(task.status)}>
                {task.status}
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Agent</p>
              <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                {task.agent_target}
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Priority</p>
              <Badge
                variant="outline"
                className={
                  metadata.priority_level === "high"
                    ? "border-red-500/20 text-red-400"
                    : metadata.priority_level === "normal"
                    ? "border-yellow-500/20 text-yellow-400"
                    : "border-zinc-500/20 text-zinc-400"
                }
              >
                {metadata.priority_level} ({task.priority})
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Type</p>
              <Badge
                variant="outline"
                className={
                  task.recurring
                    ? "border-blue-500/20 text-blue-400"
                    : "border-zinc-500/20 text-zinc-400"
                }
              >
                {task.recurring ? (
                  <>
                    <RotateCcw className="w-3 h-3 mr-1" />
                    Recurring
                  </>
                ) : (
                  "One-time"
                )}
              </Badge>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Execution Time</p>
              <p className="text-white font-mono">
                {formatDuration(execution_metrics.execution_time_seconds)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Task Information */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Task Information
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-zinc-500">Created</p>
                <p className="text-white">
                  {formatDateInTbilisi(task.created_at)}
                </p>
                <p className="text-xs text-zinc-400">
                  {formatDistanceToNowInTbilisi(task.created_at)}
                </p>
              </div>
              <div>
                <p className="text-sm text-zinc-500">Last Updated</p>
                <p className="text-white">
                  {task.updated_at ? formatDateInTbilisi(task.updated_at) : "Never"}
                </p>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Worker</p>
              <p className="text-white font-mono">
                {task.worker_id || "Unassigned"}
              </p>
            </div>

            {task.completed_at && (
              <div className="space-y-2">
                <p className="text-sm text-zinc-500">Completed</p>
                <p className="text-white">
                  {task.completed_at ? formatDateInTbilisi(task.completed_at) : "Not completed"}
                </p>
              </div>
            )}

            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Created By</p>
              <p className="text-white">
                {metadata.created_by_user ? "User" : "System"}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Execution Metrics */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Execution Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-zinc-500">Retry Count</p>
                <p className="text-white">{execution_metrics.retry_count}</p>
              </div>
              <div>
                <p className="text-sm text-zinc-500">Error Count</p>
                <p className="text-white">{execution_metrics.error_count}</p>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Has Result</p>
              <Badge variant="outline" className={execution_metrics.has_result ? "border-green-500/20 text-green-400" : "border-red-500/20 text-red-400"}>
                {execution_metrics.has_result ? "Yes" : "No"}
              </Badge>
            </div>

            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Total Events</p>
              <p className="text-white">{history.total_events}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Task Payload */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle>Task Payload</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-sm text-zinc-300 bg-zinc-950 p-4 rounded-md overflow-x-auto">
            {formatObject(task.payload)}
          </pre>
        </CardContent>
      </Card>

      {/* Task Result */}
      {task.result && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              Task Result
            </CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm text-zinc-300 bg-zinc-950 p-4 rounded-md overflow-x-auto">
              {formatObject(task.result)}
            </pre>
          </CardContent>
        </Card>
      )}

      {/* Error Log */}
      {task.error_log && task.error_log.length > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-red-500" />
              Error Log
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {task.error_log.map((error: string, index: number) => (
                <div key={index} className="text-sm text-red-400 bg-red-950/20 p-3 rounded-md">
                  {error}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent Specific Information */}
      {agent_specific && task.agent_target === "CRYPTO_SENTINEL" && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-500" />
              Crypto Sentinel Details
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-zinc-500">Recent Briefs</p>
                <p className="text-white">{agent_specific.recent_briefs_count}</p>
              </div>
              <div>
                <p className="text-sm text-zinc-500">API Usage</p>
                <div className="flex gap-2">
                  {agent_specific.api_usage.coingecko_used && (
                    <Badge variant="outline" className="border-green-500/20 text-green-400">
                      CoinGecko
                    </Badge>
                  )}
                  {agent_specific.api_usage.cryptopanic_used && (
                    <Badge variant="outline" className="border-blue-500/20 text-blue-400">
                      CryptoPanic
                    </Badge>
                  )}
                </div>
              </div>
            </div>

            {agent_specific.briefs && agent_specific.briefs.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm text-zinc-500">Recent Briefs</p>
                <div className="space-y-2">
                  {agent_specific.briefs.map((brief: any, index: number) => (
                    <div key={index} className="text-sm text-zinc-300 bg-zinc-950/50 p-3 rounded-md">
                      <p className="font-medium">{brief.date}</p>
                      <p className="text-zinc-400 text-xs">
                        {brief.market_summary?.total_market_cap?.toLocaleString()} market cap
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Event History */}
      {history.events && history.events.length > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Event History
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {history.events.map((event: TaskDetails["history"]["events"][number], index: number) => (
                <div key={index} className="flex items-start gap-3 p-3 bg-zinc-950/30 rounded-md">
                  <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium text-white">{event.event_type}</p>
                      <p className="text-xs text-zinc-400">
                        {formatDateInTbilisi(event.timestamp)}
                      </p>
                    </div>
                    <pre className="text-xs text-zinc-400 bg-zinc-950/50 p-2 rounded overflow-x-auto">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Similar Tasks */}
      {comparison.similar_tasks && comparison.similar_tasks.length > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle>Similar Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {comparison.similar_tasks.map((similarTask: TaskDetails["comparison"]["similar_tasks"][number]) => (
                <div key={similarTask.task_id} className="flex items-center justify-between p-3 bg-zinc-950/30 rounded-md">
                  <div>
                    <p className="text-sm font-medium text-white">{similarTask.title}</p>
                    <p className="text-xs text-zinc-400">
                      {formatDateInTbilisi(similarTask.created_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push(`/tasks/${similarTask.task_id}`)}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
