"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Task, TaskStatus, AgentTarget } from "@/types/api";
import {
  Plus,
  RefreshCw,
  Filter,
  Clock,
  CheckCircle,
  XCircle,
  Trash2,
  Loader2,
  ChevronDown,
  ChevronUp,
  Eye,
  RotateCcw,
  Brain,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import CreateTaskDialog from "./CreateTaskDialog";
import { formatDateInTbilisi } from "@/lib/utils";

const STATUS_OPTIONS: TaskStatus[] = [
  "PENDING",
  "PLANNING",
  "PLAN_READY",
  "APPROVED",
  "PICKED_UP",
  "EXECUTING",
  "PHASE_READY",
  "PHASE_REVIEW",
  "IN_PROGRESS",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

const AGENT_OPTIONS: AgentTarget[] = [
  "ORCHESTRATOR",
  "CRYPTO_SENTINEL",
  "JOB_HUNTER",
  "IDEAS_MACHINE",
  "META_BUILDER",
];

export default function TasksPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["tasks", statusFilter, agentFilter],
    queryFn: () =>
      api.getTasks({
        status: statusFilter === "all" ? undefined : statusFilter,
        agent_target: agentFilter === "all" ? undefined : agentFilter,
        limit: 100,
      }),
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
  });

  const createTaskMutation = useMutation({
    mutationFn: api.createTask.bind(api),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Task Queue</h1>
          <p className="text-zinc-400">Manage and monitor tasks</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["tasks"] })}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <CreateTaskDialog
            onSubmit={(data) => createTaskMutation.mutate(data)}
            isLoading={createTaskMutation.isPending}
          />
        </div>
      </div>

      {/* Filters */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardContent className="p-4">
          <div className="flex gap-4 items-center">
            <Filter className="w-4 h-4 text-zinc-500" />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-40 bg-zinc-800 border-zinc-700 text-zinc-300">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-900 border-zinc-800">
                <SelectItem value="all" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">All Status</SelectItem>
                {STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status} className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                    {status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={agentFilter} onValueChange={setAgentFilter}>
              <SelectTrigger className="w-48 bg-zinc-800 border-zinc-700 text-zinc-300">
                <SelectValue placeholder="Agent" />
              </SelectTrigger>
              <SelectContent className="bg-zinc-900 border-zinc-800">
                <SelectItem value="all" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">All Agents</SelectItem>
                {AGENT_OPTIONS.map((agent) => (
                  <SelectItem key={agent} value={agent} className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                    {agent}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Planning"
          value={tasks?.filter((t) => ["PLANNING", "PLAN_READY", "APPROVED"].includes(t.status)).length || 0}
          icon={Clock}
          color="text-purple-500"
        />
        <StatCard
          label="Executing"
          value={tasks?.filter((t) => ["EXECUTING", "PHASE_READY", "PHASE_REVIEW", "IN_PROGRESS"].includes(t.status)).length || 0}
          icon={Loader2}
          color="text-blue-500"
        />
        <StatCard
          label="Completed"
          value={tasks?.filter((t) => t.status === "COMPLETED").length || 0}
          icon={CheckCircle}
          color="text-emerald-500"
        />
        <StatCard
          label="Issues"
          value={tasks?.filter((t) => ["FAILED", "CANCELLED"].includes(t.status)).length || 0}
          icon={XCircle}
          color="text-red-500"
        />
      </div>

      {/* Task List */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">Tasks</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-zinc-500" />
            </div>
          ) : tasks && tasks.length > 0 ? (
            <div className="space-y-2">
              {tasks.map((task) => (
                <TaskRow key={task.task_id} task={task} onViewDetails={(taskId) => router.push(`/tasks/${taskId}`)} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">
              No tasks found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function TaskRow({ task, onViewDetails }: { task: Task; onViewDetails: (taskId: string) => void }) {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: api.deleteTask.bind(api),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
  const handleDelete = () => {
    if (deleteMutation.isPending) return;
    const confirmed = window.confirm(
      `Delete task ${task.task_id.slice(0, 8)}...? This cannot be undone.`
    );
    if (confirmed) {
      deleteMutation.mutate(task.task_id);
    }
  };
  const statusColors: Record<string, string> = {
    PENDING: "bg-amber-500/10 text-amber-500",
    PLANNING: "bg-purple-500/10 text-purple-500",
    PLAN_READY: "bg-cyan-500/10 text-cyan-500",
    APPROVED: "bg-green-500/10 text-green-500",
    PICKED_UP: "bg-blue-500/10 text-blue-500",
    EXECUTING: "bg-indigo-500/10 text-indigo-500",
    PHASE_READY: "bg-teal-500/10 text-teal-500",
    PHASE_REVIEW: "bg-orange-500/10 text-orange-500",
    IN_PROGRESS: "bg-blue-500/10 text-blue-500",
    COMPLETED: "bg-emerald-500/10 text-emerald-500",
    FAILED: "bg-red-500/10 text-red-500",
    CANCELLED: "bg-zinc-500/10 text-zinc-500",
  };
  const latestError = task.error_log?.length ? task.error_log[task.error_log.length - 1] : null;
  const createdAt = formatDateInTbilisi(task.created_at);
  const updatedAt = task.updated_at ? formatDateInTbilisi(task.updated_at) : "—";
  const formattedResult = formatObject(task.result);
  const formattedPayload = formatObject(task.payload);

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/50">
      <div className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="text-lg font-semibold text-white">{task.title || "Task"}</p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
            <span className="font-mono">{task.task_id.slice(0, 8)}...</span>
            <span>• {task.agent_target}</span>
            {task.worker_id && <span>• Worker {task.worker_id}</span>}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="outline" className="font-medium border-zinc-700 text-zinc-300">
            Priority: {task.priority}
          </Badge>
          {task.recurring && (
            <Badge variant="outline" className="font-medium border-blue-500/20 text-blue-400">
              <RotateCcw className="w-3 h-3 mr-1" />
              Recurring
            </Badge>
          )}
          <span className={`px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${statusColors[task.status]}`}>
            {task.status === "PLANNING" && (
              <>
                <Brain className="w-3 h-3 animate-pulse" />
                Planning
              </>
            )}
            {task.status === "PLAN_READY" && "📋 Plan Ready"}
            {task.status === "APPROVED" && "✅ Approved"}
            {task.status === "EXECUTING" && "⚡ Executing"}
            {task.status === "PHASE_READY" && "🔄 Phase Ready"}
            {task.status === "PHASE_REVIEW" && "👀 Review Phase"}
            {task.status === "COMPLETED" && "🎉 Completed"}
            {task.status === "FAILED" && "❌ Failed"}
            {task.status === "CANCELLED" && "🚫 Cancelled"}
            {task.status === "PENDING" && "⏳ Pending"}
            {task.status === "PICKED_UP" && "🚀 Started"}
            {task.status === "IN_PROGRESS" && "🔄 In Progress"}
            {!["PLANNING", "PLAN_READY", "APPROVED", "EXECUTING", "PHASE_READY", "PHASE_REVIEW", "COMPLETED", "FAILED", "CANCELLED", "PENDING", "PICKED_UP", "IN_PROGRESS"].includes(task.status) && task.status}
          </span>
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="bg-red-900/40 text-red-200 border border-red-800 hover:bg-red-800 hover:text-white p-2"
            title={deleteMutation.isPending ? "Deleting..." : "Delete task"}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpen((prev) => !prev)}
            className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
          >
            {open ? (
              <>
                Hide details <ChevronUp className="ml-2 h-4 w-4" />
              </>
            ) : (
              <>
                View details <ChevronDown className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>

      {open && (
        <div className="space-y-3 border-t border-zinc-800 bg-zinc-900/60 px-4 py-3">
          <div className="flex justify-end gap-2 mb-2">
            {task.status === "PLAN_READY" && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/tasks/${task.task_id}/plan`)}
                className="border-cyan-500/20 text-cyan-400 hover:bg-cyan-500/10"
              >
                <Eye className="w-4 h-4 mr-2" />
                Review Plan
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => onViewDetails(task.task_id)}
              className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
            >
              <Eye className="w-4 h-4 mr-2" />
              View Details
            </Button>
          </div>
          <div className="grid gap-2 text-sm text-zinc-400 md:grid-cols-4">
            <DetailField label="Created" value={createdAt} />
            <DetailField label="Updated" value={updatedAt} />
            <DetailField label="Worker" value={task.worker_id || "Unassigned"} />
            <DetailField label="Last error" value={latestError || "None"} />
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <DetailBlock
              title="Instruction / description"
              body={task.title || "No description provided."}
            />
            <DetailBlock
              title="Progress"
              body={
                task.status === "FAILED" && latestError
                  ? `❌ FAILED: ${latestError}`
                  : task.status === "COMPLETED" && formattedResult
                    ? "🎉 COMPLETED - see output below"
                    : task.status === "PLANNING"
                      ? "🤔 AI is analyzing your request and creating a detailed project plan..."
                      : task.status === "PLAN_READY"
                        ? "📋 Plan is ready for your review and approval"
                        : task.status === "APPROVED"
                          ? "✅ Plan approved - starting project execution"
                          : task.status === "EXECUTING"
                            ? "⚡ AI is building your project phase by phase"
                            : `Currently ${task.status.toLowerCase().replace("_", " ")}`
              }
            />
            <DetailBlock
              title="Payload"
              body={formattedPayload || "No payload provided."}
              isMonospace
            />
            <DetailBlock
              title="Output / result"
              body={formattedResult || "Awaiting result..."}
              isMonospace
            />
          </div>
        </div>
      )}
    </div>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md bg-zinc-900/80 p-2">
      <span className="text-xs uppercase tracking-wide text-zinc-500">{label}</span>
      <span className="text-sm text-white">{value}</span>
    </div>
  );
}

function DetailBlock({
  title,
  body,
  isMonospace = false,
}: {
  title: string;
  body: string;
  isMonospace?: boolean;
}) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{title}</p>
      <p
        className={`mt-2 text-sm text-zinc-200 ${isMonospace ? "whitespace-pre-wrap font-mono" : ""}`}
      >
        {body}
      </p>
    </div>
  );
}

function formatObject(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function StatCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <Icon className={`w-8 h-8 ${color}`} />
          <div>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-sm text-zinc-500">{label}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


