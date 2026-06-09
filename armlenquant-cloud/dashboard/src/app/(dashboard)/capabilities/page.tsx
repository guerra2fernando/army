"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Agent, CapabilityGrant, CapabilityUsage } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Shield, Loader2 } from "lucide-react";

export default function CapabilitiesPage() {
  const { data: agents, isLoading } = useQuery({
    queryKey: ["agents"],
    queryFn: () => api.getAgents(),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-7 h-7 text-emerald-500" />
            Capability Sandbox
          </h1>
          <p className="text-zinc-400">
            View per-agent grants, overrides, and recent usage.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
        </div>
      ) : agents && agents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map((agent) => (
            <AgentCapabilityCard key={agent.agent_id} agent={agent} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">No agents registered.</p>
      )}
    </div>
  );
}

function AgentCapabilityCard({ agent }: { agent: Agent }) {
  const grants: CapabilityGrant[] = agent.granted_capabilities || [];
  const usage: Record<string, CapabilityUsage> = agent.capability_usage || {};

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader>
        <CardTitle className="text-white flex items-center justify-between">
          <span>{agent.agent_name}</span>
          <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
            v{agent.version}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <Shield className="w-4 h-4 text-emerald-500" />
          Granted capabilities ({grants.length})
        </div>
        {grants.length === 0 ? (
          <p className="text-sm text-zinc-500">No explicit grants recorded.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {grants.map((grant) => (
              <Badge
                key={`${agent.agent_id}-${grant.capability_id}`}
                variant="outline"
                className="bg-zinc-800 border-zinc-700 text-zinc-200"
              >
                {grant.capability_id}
                {grant.conditions && grant.conditions.length > 0 && (
                  <span className="ml-2 text-[10px] text-amber-400">
                    +{grant.conditions.length} rules
                  </span>
                )}
              </Badge>
            ))}
          </div>
        )}

        <div className="border border-zinc-800 rounded-lg p-3 bg-zinc-950/40 space-y-2">
          <p className="text-xs text-zinc-500">Usage (today / total / remaining)</p>
          {Object.keys(usage).length === 0 ? (
            <p className="text-xs text-zinc-500">No usage reported yet.</p>
          ) : (
            <div className="space-y-1">
              {Object.entries(usage).map(([cap, stats]) => (
                <div key={cap} className="flex items-center justify-between text-sm">
                  <span className="text-zinc-200">{cap}</span>
                  <span className="text-zinc-400 text-xs">
                    {stats.today_count ?? 0} / {stats.total_count ?? 0} /{" "}
                    {stats.quota_remaining ?? "∞"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

