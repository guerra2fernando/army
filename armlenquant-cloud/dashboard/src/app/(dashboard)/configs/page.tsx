"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Agent, AgentConfigVersion } from "@/types/api";
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
import { toast } from "sonner";
import { Layers, Loader2, RefreshCw, Undo2 } from "lucide-react";

export default function ConfigsPage() {
  const queryClient = useQueryClient();
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents(),
  });

  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedAgent && agents && agents.length > 0) {
      setSelectedAgent(agents[0].agent_id);
    }
  }, [agents, selectedAgent]);

  const { data: versions, isLoading: versionsLoading } = useQuery({
    queryKey: ["agent-configs", selectedAgent],
    queryFn: () => api.getAgentConfigVersions(selectedAgent as string),
    enabled: !!selectedAgent,
  });

  const rollback = useMutation({
    mutationFn: ({ agentId, version }: { agentId: string; version: string }) =>
      api.rollbackAgentConfig(agentId, version),
    onSuccess: () => {
      toast.success("Rolled back config");
      queryClient.invalidateQueries({ queryKey: ["agent-configs"] });
      queryClient.invalidateQueries({ queryKey: ["agents"] });
    },
    onError: () => toast.error("Rollback failed"),
  });

  const activeVersion = useMemo(
    () => versions?.find((v) => v.is_active) || versions?.[0],
    [versions]
  );

  const currentAgent: Agent | undefined = agents?.find((a) => a.agent_id === selectedAgent);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Layers className="w-7 h-7 text-emerald-500" />
            Config Versioning
          </h1>
          <p className="text-zinc-400">
            Inspect active versions, diffs, and rollback safely.
          </p>
        </div>
        <Button
          variant="outline"
          className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["agent-configs", selectedAgent] })}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">Agent selector</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col md:flex-row gap-4 md:items-center">
          <Select
            value={selectedAgent || undefined}
            onValueChange={setSelectedAgent}
            disabled={agentsLoading}
          >
            <SelectTrigger className="w-full md:w-80 bg-zinc-900 border-zinc-800 text-zinc-200">
              <SelectValue placeholder="Select agent" />
            </SelectTrigger>
            <SelectContent className="bg-zinc-900 border-zinc-800">
              {agents?.map((agent) => (
                <SelectItem
                  key={agent.agent_id}
                  value={agent.agent_id}
                  className="text-zinc-200 focus:bg-zinc-800 focus:text-white"
                >
                  {agent.agent_name} ({agent.location})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {currentAgent && (
            <Badge variant="outline" className="bg-zinc-800 border-zinc-700 text-zinc-200">
              Active version: {currentAgent.config_version || "unknown"}
            </Badge>
          )}
        </CardContent>
      </Card>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-500" />
            Version history
          </CardTitle>
        </CardHeader>
        <CardContent>
          {versionsLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
            </div>
          ) : versions && versions.length > 0 ? (
            <div className="space-y-3">
              {versions.map((version) => (
                <div
                  key={version.version}
                  className="border border-zinc-800 rounded-lg p-4 bg-zinc-950/60 flex flex-col gap-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-3">
                      <Badge
                        variant="outline"
                        className={
                          version.is_active
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : "bg-zinc-800 text-zinc-300 border-zinc-700"
                        }
                      >
                        v{version.version}
                      </Badge>
                      {version.schema_version && (
                        <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                          schema {version.schema_version}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {!version.is_active && selectedAgent && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            rollback.mutate({ agentId: selectedAgent, version: version.version })
                          }
                          disabled={rollback.isPending}
                          className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                        >
                          <Undo2 className="w-4 h-4 mr-2" />
                          Rollback
                        </Button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-zinc-300 line-clamp-3">
                    {version.prompt_template || "No prompt recorded"}
                  </p>
                  <div className="text-xs text-zinc-500 flex flex-wrap gap-2">
                    {version.created_by && <span>By {version.created_by}</span>}
                    {version.created_at && (
                      <span>· {new Date(version.created_at).toLocaleString()}</span>
                    )}
                    {version.notes && <span>· {version.notes}</span>}
                  </div>
                  {version.performance_baseline && (
                    <div className="text-xs text-zinc-400">
                      Baseline: {Object.entries(version.performance_baseline)
                        .map(([k, v]) => `${k}: ${String(v)}`)
                        .join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-zinc-500">No configuration versions found.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

