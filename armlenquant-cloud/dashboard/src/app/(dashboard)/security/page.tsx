"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SafetyStatus } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Shield, KeyRound, Lock, Network, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";

export default function SecurityPage() {
  const { user } = useAuth();

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.getDetailedHealth(),
    refetchInterval: 10000,
  });

  const { data: safety, isLoading: safetyLoading } = useQuery<SafetyStatus>({
    queryKey: ["safety-status", "security"],
    queryFn: () => api.getSafetyStatus(),
    enabled: !!user?.is_admin,
    retry: false,
  });

  const dbStatus = health?.data?.database || "unknown";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white flex items-center gap-2">
          <Shield className="w-7 h-7 text-emerald-500" />
          Security Posture
        </h1>
        <p className="text-zinc-400">
          mTLS, signed agent traffic, scoped tokens, and orchestrator guardrails.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SecurityCard
          title="mTLS & certificates"
          icon={<Lock className="w-5 h-5" />}
          status="Protected"
          detail="Mutual TLS required between cloud and local agents."
        />
        <SecurityCard
          title="Signed agent traffic"
          icon={<KeyRound className="w-5 h-5" />}
          status="HMAC"
          detail="All agent requests are HMAC signed with rotating keys."
        />
        <SecurityCard
          title="Scoped tokens"
          icon={<Network className="w-5 h-5" />}
          status="Least privilege"
          detail="Tokens carry explicit scopes and usage caps."
        />
      </div>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white">System health & auth signals</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <InfoItem label="Database" value={dbStatus} tone={dbStatus === "connected" ? "green" : "amber"} />
          <InfoItem
            label="Agents online"
            value={`${health?.data?.agents?.active ?? 0}/${health?.data?.agents?.total ?? 0}`}
            tone="blue"
          />
          <InfoItem
            label="Tasks pending"
            value={health?.data?.task_queue?.pending ?? 0}
            tone={(health?.data?.task_queue?.pending ?? 0) > 20 ? "amber" : "green"}
          />
        </CardContent>
      </Card>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-500" />
            Orchestrator safety state
          </CardTitle>
        </CardHeader>
        <CardContent>
          {user?.is_admin ? (
            safetyLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
              </div>
            ) : safety ? (
              <div className="flex flex-wrap gap-3 items-center">
                <Badge
                  variant="outline"
                  className={
                    safety.kill_switch_active
                      ? "bg-red-500/10 text-red-400 border-red-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  }
                >
                  Kill switch: {safety.kill_switch_active ? "ACTIVE" : "inactive"}
                </Badge>
                <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                  Orchestrator enabled: {safety.orchestrator_enabled ? "yes" : "no"}
                </Badge>
                <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                  Spawn budgets: {safety.budgets.length}
                </Badge>
              </div>
            ) : (
              <p className="text-sm text-zinc-500">Unable to load safety status.</p>
            )
          ) : (
            <p className="text-sm text-zinc-500">
              Admin access is required to view kill switch and spawn budgets.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function SecurityCard({
  title,
  status,
  detail,
  icon,
}: {
  title: string;
  status: string;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="p-3 rounded-full bg-zinc-800 text-emerald-400">{icon}</div>
          <Badge variant="outline" className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
            {status}
          </Badge>
        </div>
        <h3 className="mt-3 text-lg text-white font-semibold">{title}</h3>
        <p className="text-sm text-zinc-400 mt-1">{detail}</p>
      </CardContent>
    </Card>
  );
}

function InfoItem({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: string | number;
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
    <div className="border border-zinc-800 rounded-lg p-3 bg-zinc-950/40">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className={`text-lg font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

