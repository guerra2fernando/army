"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Task } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertTriangle,
  Clock3,
  History,
  RefreshCw,
  ShieldCheck,
  Zap,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

export default function ReliabilityPage() {
  const queryClient = useQueryClient();
  const { data: tasks, isLoading } = useQuery({
    queryKey: ["tasks", "reliability"],
    queryFn: () => api.getTasks({ limit: 200 }),
    refetchInterval: 5000,
  });

  const recover = useMutation({
    mutationFn: () => api.recoverLeases(),
    onSuccess: (resp) => {
      toast.success(resp.message || "Recovered expired leases");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Failed to recover leases"),
  });

  const now = new Date();
  const metrics = useMemo(() => buildMetrics(tasks || [], now), [tasks, now]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="w-7 h-7 text-emerald-500" />
            Reliability & Lease Health
          </h1>
          <p className="text-zinc-400">
            Monitor leases, idempotency hits, and recover stuck tasks.
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["tasks", "reliability"] })}
          className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Pending"
          value={metrics.pending}
          icon={<Clock3 className="w-5 h-5" />}
        />
        <StatCard
          title="In Progress"
          value={metrics.inProgress}
          icon={<Activity className="w-5 h-5" />}
          tone="blue"
        />
        <StatCard
          title="Stuck (lease)"
          value={metrics.stuck}
          icon={<AlertTriangle className="w-5 h-5" />}
          tone={metrics.stuck > 0 ? "amber" : "green"}
        />
        <StatCard
          title="Idempotency hits"
          value={metrics.idempotencyHits}
          icon={<History className="w-5 h-5" />}
          tone={metrics.idempotencyHits > 0 ? "amber" : "green"}
        />
      </div>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            Stuck tasks (lease expired)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            </div>
          ) : metrics.stuckTasks.length === 0 ? (
            <p className="text-sm text-zinc-500">No stuck tasks detected.</p>
          ) : (
            <div className="space-y-2">
              {metrics.stuckTasks.map((task) => (
                <div
                  key={task.task_id}
                  className="flex items-center justify-between bg-zinc-950/50 border border-zinc-800 rounded-lg px-3 py-2"
                >
                  <div>
                    <p className="text-white font-medium">{task.title || task.agent_target}</p>
                    <p className="text-xs text-zinc-500">
                      Lease until {task.lease_until ? new Date(task.lease_until).toLocaleString() : "unknown"} ·{" "}
                      {task.status}
                    </p>
                  </div>
                  <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/20">
                    {task.agent_target}
                  </Badge>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-500" />
            Idempotency hits (deduped payloads)
          </CardTitle>
          <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
            Window: recent tasks
          </Badge>
        </CardHeader>
        <CardContent>
          {metrics.idempotentGroups.length === 0 ? (
            <p className="text-sm text-zinc-500">No duplicate payloads detected.</p>
          ) : (
            <div className="space-y-2">
              {metrics.idempotentGroups.map((group) => (
                <div
                  key={group.key}
                  className="border border-zinc-800 rounded-lg p-3 bg-zinc-950/50"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white font-semibold">Key: {group.key}</p>
                      <p className="text-xs text-zinc-500">
                        {group.tasks.length} hits · First {new Date(group.firstCreated).toLocaleString()}
                      </p>
                    </div>
                    <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                      {group.agentTargets.join(", ")}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-emerald-500" />
            Recovery actions
          </CardTitle>
          <Button
            size="sm"
            onClick={() => recover.mutate()}
            disabled={recover.isPending}
            className="bg-emerald-500 hover:bg-emerald-600 text-black"
          >
            {recover.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <RefreshCw className="w-4 h-4 mr-2" />
            )}
            Recover expired leases
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-zinc-400">
            Trigger lease recovery for tasks stuck on crashed workers. This re-queues expired
            leases and keeps execution idempotent.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function buildMetrics(tasks: Task[], now: Date) {
  const pending = tasks.filter((t) => t.status === "PENDING").length;
  const inProgress = tasks.filter((t) =>
    ["IN_PROGRESS", "PICKED_UP", "EXECUTING", "PHASE_READY", "PHASE_REVIEW"].includes(t.status)
  ).length;

  const stuckTasks = tasks.filter((t) => {
    if (!t.lease_until) return false;
    const leaseTime = new Date(t.lease_until);
    return (
      leaseTime < now &&
      ["IN_PROGRESS", "PICKED_UP", "EXECUTING", "PHASE_READY", "PHASE_REVIEW"].includes(t.status)
    );
  });

  const idempotentGroups = Object.values(
    tasks.reduce<Record<string, { key: string; tasks: Task[]; firstCreated: string; agentTargets: string[] }>>(
      (acc, task) => {
        const key = task.idempotency_key;
        if (!key) return acc;
        if (!acc[key]) {
          acc[key] = {
            key,
            tasks: [],
            firstCreated: task.created_at,
            agentTargets: [],
          };
        }
        acc[key].tasks.push(task);
        acc[key].firstCreated =
          new Date(task.created_at) < new Date(acc[key].firstCreated) ? task.created_at : acc[key].firstCreated;
        if (!acc[key].agentTargets.includes(task.agent_target)) {
          acc[key].agentTargets.push(task.agent_target);
        }
        return acc;
      },
      {}
    )
  ).filter((group) => group.tasks.length > 1);

  return {
    pending,
    inProgress,
    stuck: stuckTasks.length,
    stuckTasks,
    idempotencyHits: idempotentGroups.reduce((acc, group) => acc + group.tasks.length - 1, 0),
    idempotentGroups,
  };
}

function StatCard({
  title,
  value,
  icon,
  tone = "neutral",
}: {
  title: string;
  value: number;
  icon: React.ReactNode;
  tone?: "neutral" | "green" | "blue" | "amber";
}) {
  const toneClass =
    tone === "green"
      ? "text-emerald-400"
      : tone === "blue"
      ? "text-blue-400"
      : tone === "amber"
      ? "text-amber-400"
      : "text-zinc-300";
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-zinc-500">{title}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-3 rounded-full bg-zinc-800 ${toneClass}`}>{icon}</div>
      </CardContent>
    </Card>
  );
}

