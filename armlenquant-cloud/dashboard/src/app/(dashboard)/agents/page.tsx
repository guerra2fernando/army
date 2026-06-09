"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Agent } from "@/types/api";
import {
  Bot,
  Cloud,
  Laptop,
  Play,
  Pause,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function AgentsPage() {
  const queryClient = useQueryClient();

  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents(),
    refetchInterval: 10000,
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ name, status }: { name: string; status: string }) =>
      api.updateAgentStatus(name, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
  });

  const toggleAgent = (agent: Agent) => {
    const newStatus = agent.status === "ACTIVE" ? "PAUSED" : "ACTIVE";
    updateStatusMutation.mutate({ name: agent.agent_name, status: newStatus });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Agent Barracks</h1>
          <p className="text-zinc-400">Monitor and control your agents</p>
        </div>
        <Button
          variant="outline"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["agents"] })}
          className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents?.map((agent) => (
          <AgentCard key={agent.agent_id} agent={agent} onToggle={toggleAgent} />
        ))}
        {isLoading && (
          <>
            <AgentCardSkeleton />
            <AgentCardSkeleton />
            <AgentCardSkeleton />
          </>
        )}
      </div>

      {/* Agent Details Table */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">Agent Details</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-400">Agent</TableHead>
                <TableHead className="text-zinc-400">Location</TableHead>
                <TableHead className="text-zinc-400">Trigger</TableHead>
                <TableHead className="text-zinc-400">Success Rate</TableHead>
                <TableHead className="text-zinc-400">Total Runs</TableHead>
                <TableHead className="text-zinc-400">Last Run</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {agents?.map((agent) => (
                <TableRow key={agent.agent_id} className="border-zinc-800 hover:bg-zinc-800/50">
                  <TableCell className="font-medium text-white">
                    {agent.agent_name}
                    <span className="text-xs text-zinc-500 ml-2">
                      v{agent.version}
                    </span>
                  </TableCell>
                  <TableCell className="text-zinc-300">
                    {agent.location === "CLOUD" ? (
                      <span className="flex items-center gap-1">
                        <Cloud className="w-4 h-4" /> Cloud
                      </span>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Laptop className="w-4 h-4" /> Local
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-zinc-300">{agent.trigger_type}</TableCell>
                  <TableCell className="text-zinc-300">
                    {(agent.performance.success_rate * 100).toFixed(0)}%
                  </TableCell>
                  <TableCell className="text-zinc-300">{agent.performance.total_runs}</TableCell>
                  <TableCell className="text-zinc-300">
                    {agent.performance.last_run_at
                      ? new Date(agent.performance.last_run_at).toLocaleString()
                      : "Never"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={agent.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function AgentCard({
  agent,
  onToggle,
}: {
  agent: Agent;
  onToggle: (agent: Agent) => void;
}) {
  const statusIcon = {
    ACTIVE: <CheckCircle className="w-4 h-4 text-emerald-500" />,
    PAUSED: <Pause className="w-4 h-4 text-amber-500" />,
    FAILED: <XCircle className="w-4 h-4 text-red-500" />,
    INITIALIZING: <Clock className="w-4 h-4 text-blue-500" />,
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-zinc-800">
              <Bot className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h3 className="font-semibold text-white">{agent.agent_name}</h3>
              <p className="text-sm text-zinc-500">v{agent.version}</p>
            </div>
          </div>
          {statusIcon[agent.status as keyof typeof statusIcon]}
        </div>

        <div className="mt-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-zinc-500">Success Rate</span>
            <span className="text-zinc-300">{(agent.performance.success_rate * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-zinc-500">Total Runs</span>
            <span className="text-zinc-300">{agent.performance.total_runs}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-zinc-500">Location</span>
            <span className="flex items-center gap-1 text-zinc-300">
              {agent.location === "CLOUD" ? (
                <Cloud className="w-3 h-3" />
              ) : (
                <Laptop className="w-3 h-3" />
              )}
              {agent.location}
            </span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-zinc-800">
          <Button
            variant={agent.status === "ACTIVE" ? "outline" : "default"}
            size="sm"
            className={
              agent.status === "ACTIVE"
                ? "w-full border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                : "w-full bg-emerald-500 hover:bg-emerald-600 text-black"
            }
            onClick={() => onToggle(agent)}
          >
            {agent.status === "ACTIVE" ? (
              <>
                <Pause className="w-4 h-4 mr-2" /> Pause
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" /> Resume
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentCardSkeleton() {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-zinc-800 rounded-lg" />
            <div className="space-y-2">
              <div className="w-24 h-4 bg-zinc-800 rounded" />
              <div className="w-16 h-3 bg-zinc-800 rounded" />
            </div>
          </div>
          <div className="space-y-2">
            <div className="w-full h-4 bg-zinc-800 rounded" />
            <div className="w-full h-4 bg-zinc-800 rounded" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ACTIVE: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    PAUSED: "bg-amber-500/10 text-amber-500 border-amber-500/20",
    FAILED: "bg-red-500/10 text-red-500 border-red-500/20",
    INITIALIZING: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  };

  return (
    <Badge variant="outline" className={styles[status] || styles.PAUSED}>
      {status}
    </Badge>
  );
}

