"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Workflow, WorkflowStatus, WorkflowStep } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  CheckCircle2,
  GitBranch,
  Loader2,
  Pause,
  Play,
  Shield,
  TimerReset,
  Workflow as WorkflowIcon,
  Ban,
  CircleDot,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";

const STATUS_OPTIONS: WorkflowStatus[] = [
  "PENDING",
  "RUNNING",
  "PAUSED",
  "COMPLETED",
  "FAILED",
  "CANCELLED",
];

export default function WorkflowsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const {
    data: workflows,
    isLoading,
    isFetching,
  } = useQuery({
    queryKey: ["workflows", statusFilter],
    queryFn: () =>
      api.listWorkflows({
        status: statusFilter === "all" ? undefined : statusFilter,
        limit: 100,
      }),
    refetchInterval: 4000,
  });

  const updateStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: WorkflowStatus }) =>
      api.updateWorkflowStatus(id, status),
    onSuccess: () => {
      toast.success("Workflow status updated");
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: () => toast.error("Failed to update workflow"),
  });

  const approve = useMutation({
    mutationFn: (id: string) => api.approveWorkflow(id),
    onSuccess: () => {
      toast.success("Workflow approved");
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: () => toast.error("Failed to approve workflow"),
  });

  const reject = useMutation({
    mutationFn: (id: string) => api.rejectWorkflow(id, "Rejected from dashboard"),
    onSuccess: () => {
      toast.success("Workflow rejected");
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: () => toast.error("Failed to reject workflow"),
  });

  const resume = useMutation({
    mutationFn: (id: string) => api.resumeWorkflow(id),
    onSuccess: () => {
      toast.success("Workflow resumed");
      queryClient.invalidateQueries({ queryKey: ["workflows"] });
    },
    onError: () => toast.error("Failed to resume workflow"),
  });

  const stats = useMemo(() => {
    const all = workflows || [];
    return {
      total: all.length,
      pending: all.filter((w) => w.status === "PENDING").length,
      running: all.filter((w) => w.status === "RUNNING").length,
      approvals: all.filter((w) => w.approval_state === "PENDING").length,
    };
  }, [workflows]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <GitBranch className="w-7 h-7 text-emerald-500" />
            Workflows Command Center
          </h1>
          <p className="text-zinc-400">
            Track workflow timelines, approvals, and recovery actions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {isFetching && <Loader2 className="w-4 h-4 animate-spin text-zinc-500" />}
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40 bg-zinc-900 border-zinc-800 text-zinc-200">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-900 border-zinc-800">
              <SelectItem value="all" className="text-zinc-200 focus:bg-zinc-800">
                All Status
              </SelectItem>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem
                  key={s}
                  value={s}
                  className="text-zinc-200 focus:bg-zinc-800 focus:text-white"
                >
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total"
          value={stats.total}
          icon={<WorkflowIcon className="w-5 h-5" />}
          tone="neutral"
        />
        <StatCard
          title="Pending"
          value={stats.pending}
          icon={<CircleDot className="w-5 h-5" />}
          tone="amber"
        />
        <StatCard
          title="Running"
          value={stats.running}
          icon={<Play className="w-5 h-5" />}
          tone="green"
        />
        <StatCard
          title="Approvals"
          value={stats.approvals}
          icon={<Shield className="w-5 h-5" />}
          tone="blue"
        />
      </div>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <WorkflowIcon className="w-5 h-5 text-emerald-500" />
            Workflows
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            </div>
          ) : workflows && workflows.length > 0 ? (
            <div className="space-y-3">
              {workflows.map((workflow) => {
                const isExpanded = expanded === workflow.workflow_id;
                return (
                  <div
                    key={workflow.workflow_id}
                    className="rounded-lg border border-zinc-800 bg-zinc-950/40 overflow-hidden"
                  >
                    <button
                      className="w-full text-left px-4 py-3 flex items-center justify-between hover:bg-zinc-900/60 transition-colors"
                      onClick={() =>
                        setExpanded(isExpanded ? null : workflow.workflow_id)
                      }
                    >
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className={statusColor(workflow.status)}>
                          {workflow.status}
                        </Badge>
                        <div>
                          <p className="text-white font-semibold">
                            {workflow.type} · {workflow.workflow_id.slice(0, 6)}
                          </p>
                          <p className="text-xs text-zinc-500">
                            {workflow.steps.length} steps · Priority {workflow.priority}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {workflow.approval_state === "PENDING" && (
                          <Badge variant="secondary" className="bg-amber-500/10 text-amber-400">
                            Approval needed
                          </Badge>
                        )}
                        <span className="text-xs text-zinc-500">
                          Updated {workflow.updated_at ? new Date(workflow.updated_at).toLocaleString() : "—"}
                        </span>
                      </div>
                    </button>

                    {isExpanded && (
                      <div className="border-t border-zinc-800 bg-zinc-950/80">
                        <div className="px-4 py-3 flex flex-wrap gap-2 items-center">
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={updateStatus.isPending}
                            onClick={() =>
                              updateStatus.mutate({
                                id: workflow.workflow_id,
                                status:
                                  workflow.status === "PAUSED" ? "RUNNING" : "PAUSED",
                              })
                            }
                            className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
                          >
                            {workflow.status === "PAUSED" ? (
                              <>
                                <Play className="w-4 h-4 mr-2" />
                                Resume
                              </>
                            ) : (
                              <>
                                <Pause className="w-4 h-4 mr-2" />
                                Pause
                              </>
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={updateStatus.isPending}
                            onClick={() =>
                              updateStatus.mutate({
                                id: workflow.workflow_id,
                                status: "CANCELLED",
                              })
                            }
                            className="border-red-500/40 text-red-400 hover:bg-red-500/10"
                          >
                            <Ban className="w-4 h-4 mr-2" />
                            Cancel
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={resume.isPending}
                            onClick={() => resume.mutate(workflow.workflow_id)}
                            className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                          >
                            <TimerReset className="w-4 h-4 mr-2" />
                            Resume from checkpoint
                          </Button>
                          {workflow.approval_state === "PENDING" && (
                            <>
                              <Button
                                size="sm"
                                onClick={() => approve.mutate(workflow.workflow_id)}
                                disabled={approve.isPending}
                                className="bg-emerald-500 hover:bg-emerald-600 text-black"
                              >
                                <CheckCircle2 className="w-4 h-4 mr-2" />
                                Approve
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => reject.mutate(workflow.workflow_id)}
                                disabled={reject.isPending}
                                className="border-amber-500/40 text-amber-400 hover:bg-amber-500/10"
                              >
                                <TriangleAlert className="w-4 h-4 mr-2" />
                                Reject
                              </Button>
                            </>
                          )}
                        </div>

                        <div className="px-4 pb-4 space-y-3">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <InfoItem label="Created By" value={workflow.created_by} />
                            <InfoItem
                              label="Approval"
                              value={workflow.approval_state || "N/A"}
                            />
                            <InfoItem
                              label="Current Step"
                              value={`${workflow.current_step + 1}/${workflow.steps.length}`}
                            />
                          </div>
                          <div className="border border-zinc-800 rounded-lg p-3">
                            <p className="text-sm text-zinc-400 mb-2">Step timeline</p>
                            <div className="space-y-2">
                              {workflow.steps.map((step, idx) => (
                                <StepRow
                                  key={step.step_id}
                                  step={step}
                                  index={idx}
                                  isCurrent={idx === workflow.current_step}
                                />
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-zinc-500">
              No workflows found
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function statusColor(status: WorkflowStatus) {
  switch (status) {
    case "RUNNING":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "PAUSED":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "FAILED":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    case "COMPLETED":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "CANCELLED":
      return "bg-zinc-800 text-zinc-400 border-zinc-800";
    default:
      return "bg-zinc-800 text-zinc-300 border-zinc-700";
  }
}

function stepBadge(status: WorkflowStep["status"]) {
  switch (status) {
    case "COMPLETED":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "RUNNING":
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    case "FAILED":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    case "CANCELLED":
      return "bg-zinc-800 text-zinc-400 border-zinc-800";
    default:
      return "bg-zinc-800 text-zinc-300 border-zinc-700";
  }
}

function StatCard({
  title,
  value,
  icon,
  tone,
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  tone: "neutral" | "green" | "blue" | "amber";
}) {
  const colors: Record<"neutral" | "green" | "blue" | "amber", string> = {
    neutral: "text-zinc-300",
    green: "text-emerald-400",
    blue: "text-blue-400",
    amber: "text-amber-400",
  };
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">{title}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-full bg-zinc-800 ${colors[tone]}`}>{icon}</div>
      </CardContent>
    </Card>
  );
}

function StepRow({
  step,
  index,
  isCurrent,
}: {
  step: WorkflowStep;
  index: number;
  isCurrent: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <div
        className={`mt-1 w-2 h-2 rounded-full ${
          isCurrent ? "bg-emerald-500" : "bg-zinc-700"
        }`}
      />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm text-white font-medium">
            {index + 1}. {step.name}
          </p>
          <Badge variant="outline" className={stepBadge(step.status)}>
            {step.status}
          </Badge>
          {step.approval_required && (
            <Badge variant="outline" className="bg-amber-500/10 text-amber-400 border-amber-500/20">
              Approval {step.approval_state || "PENDING"}
            </Badge>
          )}
        </div>
        <p className="text-xs text-zinc-500">
          Agent: {step.agent_target}{" "}
          {step.started_at && `· Started ${new Date(step.started_at).toLocaleString()}`}
          {step.completed_at && ` · Completed ${new Date(step.completed_at).toLocaleString()}`}
        </p>
        {step.error && <p className="text-xs text-red-400 mt-1">{step.error}</p>}
      </div>
    </div>
  );
}

function InfoItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-zinc-800 rounded-lg p-3 bg-zinc-900/40">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="text-sm text-white font-semibold truncate">{value}</p>
    </div>
  );
}

