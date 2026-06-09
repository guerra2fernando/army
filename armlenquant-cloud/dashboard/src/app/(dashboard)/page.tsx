"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient, QueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  Bot,
  ListTodo,
  TrendingUp,
  Briefcase,
  Activity,
  ArrowRight,
  Send,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { toast } from "sonner";

export default function DashboardPage() {
  const [command, setCommand] = useState("");
  const queryClient = useQueryClient();

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getDetailedHealth(),
    refetchInterval: 30000,
    retry: false,
  });

  const { data: agents } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents(),
  });

  const { data: tasks, refetch: refetchTasks } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => api.getTasks({ limit: 5 }),
  });

  // Natural language command mutation - sends to Orchestrator
  const commandMutation = useMutation({
    mutationFn: (instruction: string) => api.createTask({
      agent_target: "ORCHESTRATOR",
      payload: { instruction, action: "process" },
      priority: 5,
    }),
    onSuccess: () => {
      toast.success("Task sent to Orchestrator!", {
        description: "The AI will route your request to the right agent.",
      });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => {
      toast.error("Failed to create task", {
        description: "Please check if the API is running.",
      });
    },
  });

  const systemData = health?.data;
  const activeAgents = agents?.filter((a) => a.status === "ACTIVE").length || 0;
  const totalAgents = agents?.length || 0;
  const pendingTasks = systemData?.task_queue?.pending || tasks?.filter(t => t.status === "PENDING").length || 0;

  const handleCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      commandMutation.mutate(command.trim());
      setCommand("");
    }
  };

  return (
    <div className="space-y-6">
      {/* Command Input */}
      <Card className="bg-gradient-to-r from-emerald-500/10 via-emerald-500/5 to-transparent border-emerald-500/20">
        <CardContent className="p-6">
          <form onSubmit={handleCommand} className="flex gap-4">
            <input
              type="text"
              placeholder="What are we doing today? (e.g., 'Find Python jobs in London', 'Analyze BTC', 'Scaffold a habit tracker app')"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              disabled={commandMutation.isPending}
              className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-lg px-4 py-3 text-lg text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
            />
            <Button
              type="submit"
              size="lg"
              disabled={commandMutation.isPending || !command.trim()}
              className="px-6 bg-emerald-500 hover:bg-emerald-600 text-black font-semibold disabled:opacity-50"
            >
              {commandMutation.isPending ? (
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              ) : (
                <Send className="w-5 h-5 mr-2" />
              )}
              Execute
            </Button>
          </form>
          <p className="text-xs text-zinc-500 mt-2">
            💡 Just describe what you want in plain English. The AI Orchestrator will route it to the right agent.
          </p>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active Agents"
          value={`${activeAgents}/${totalAgents}`}
          icon={Bot}
          status="active"
        />
        <StatCard
          title="Pending Tasks"
          value={pendingTasks.toString()}
          icon={ListTodo}
          status={pendingTasks > 0 ? "warning" : "active"}
        />
        <StatCard
          title="Crypto Signal"
          value="BULLISH"
          icon={TrendingUp}
          status="active"
          subtitle="SOL: BUY (80%)"
        />
        <StatCard
          title="Job Drafts"
          value="5"
          icon={Briefcase}
          status="active"
          subtitle="Ready to review"
        />
      </div>

      {/* Activity & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Stream */}
        <Card className="lg:col-span-2 bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Activity className="w-5 h-5 text-emerald-500" />
              Activity Stream
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tasks?.slice(0, 5).map((task) => (
                <div
                  key={task.task_id}
                  className="flex items-center justify-between py-3 border-b border-zinc-800 last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    <div>
                      <p className="font-medium text-white">{task.agent_target}</p>
                      <p className="text-sm text-zinc-500">
                        {new Date(task.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      task.status === "COMPLETED"
                        ? "default"
                        : task.status === "FAILED"
                        ? "destructive"
                        : "secondary"
                    }
                    className={
                      task.status === "COMPLETED"
                        ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                        : task.status === "FAILED"
                        ? "bg-red-500/10 text-red-500 border-red-500/20"
                        : "bg-zinc-800 text-zinc-400 border-zinc-700"
                    }
                  >
                    {task.status}
                  </Badge>
                </div>
              ))}
              {(!tasks || tasks.length === 0) && (
                <p className="text-zinc-500 text-center py-8">
                  No recent activity
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <QuickActionsCard queryClient={queryClient} />
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  status,
  subtitle,
}: {
  title: string;
  value: string;
  icon: React.ElementType;
  status: "active" | "warning" | "error";
  subtitle?: string;
}) {
  const statusColors = {
    active: "text-emerald-500",
    warning: "text-amber-500",
    error: "text-red-500",
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-zinc-400">{title}</p>
            <p className="text-2xl font-bold text-white mt-1">{value}</p>
            {subtitle && (
              <p className="text-sm text-zinc-500 mt-1">{subtitle}</p>
            )}
          </div>
          <div className={`p-3 rounded-full bg-zinc-800 ${statusColors[status]}`}>
            <Icon className="w-6 h-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function QuickActionsCard({ queryClient }: { queryClient: QueryClient }) {
  const jobSearchMutation = useMutation({
    mutationFn: () => api.createTask({
      agent_target: "JOB_HUNTER",
      payload: { action: "search" },
      priority: 5,
    }),
    onSuccess: () => {
      toast.success("Job search started!", {
        description: "Job Hunter is now searching for opportunities.",
      });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => {
      toast.error("Failed to start job search");
    },
  });

  const cryptoBriefMutation = useMutation({
    mutationFn: () => api.generateCryptoBrief(),
    onSuccess: () => {
      toast.success("Crypto brief generated!", {
        description: "Check the Crypto page for today's analysis.",
      });
    },
    onError: () => {
      toast.error("Failed to generate crypto brief");
    },
  });

  const newProjectMutation = useMutation({
    mutationFn: () => api.createTask({
      agent_target: "IDEAS_MACHINE",
      payload: { action: "scaffold", description: "New project idea" },
      priority: 5,
    }),
    onSuccess: () => {
      toast.success("Project scaffolding started!", {
        description: "Ideas Machine will create your project structure.",
      });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => {
      toast.error("Failed to start project scaffolding");
    },
  });

  const isAnyLoading = jobSearchMutation.isPending || cryptoBriefMutation.isPending || newProjectMutation.isPending;

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-white">Quick Actions</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <QuickAction
          title="Search for Jobs"
          description="Run job search with current parameters"
          onClick={() => jobSearchMutation.mutate()}
          isLoading={jobSearchMutation.isPending}
          disabled={isAnyLoading}
        />
        <QuickAction
          title="Generate Crypto Brief"
          description="Get today's market analysis"
          onClick={() => cryptoBriefMutation.mutate()}
          isLoading={cryptoBriefMutation.isPending}
          disabled={isAnyLoading}
        />
        <QuickAction
          title="New Project"
          description="Scaffold a new project idea"
          onClick={() => newProjectMutation.mutate()}
          isLoading={newProjectMutation.isPending}
          disabled={isAnyLoading}
        />
        <QuickAction
          title="View All Tasks"
          description="See task queue status"
          href="/tasks"
        />
      </CardContent>
    </Card>
  );
}

function QuickAction({
  title,
  description,
  onClick,
  href,
  isLoading,
  disabled,
}: {
  title: string;
  description: string;
  onClick?: () => void;
  href?: string;
  isLoading?: boolean;
  disabled?: boolean;
}) {
  const content = (
    <>
      <div>
        <p className="font-medium text-white">{title}</p>
        <p className="text-sm text-zinc-500">{description}</p>
      </div>
      {isLoading ? (
        <Loader2 className="w-5 h-5 text-emerald-500 animate-spin" />
      ) : (
        <ArrowRight className="w-5 h-5 text-zinc-500" />
      )}
    </>
  );

  const className =
    "w-full flex items-center justify-between p-3 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed";

  if (href) {
    return (
      <Link href={href} className={className}>
        {content}
      </Link>
    );
  }

  return (
    <button onClick={onClick} className={className} disabled={disabled}>
      {content}
    </button>
  );
}

