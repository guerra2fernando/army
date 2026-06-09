"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { SafetyStatus, SpawnBudget } from "@/types/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertOctagon,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Power,
  RefreshCw,
  Save,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/hooks/use-auth";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function SafetyPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [newBudget, setNewBudget] = useState({
    scope_type: "GLOBAL",
    agent_type_filter: "",
    max_spawns: 5,
    time_window: "DAILY",
    action_on_exceed: "BLOCK",
    cooldown_minutes: 60,
  });

  const {
    data: safety,
    isLoading,
    isError,
    error,
  } = useQuery<SafetyStatus>({
    queryKey: ["safety-status"],
    queryFn: () => api.getSafetyStatus(),
    enabled: !!user?.is_admin,
    retry: false,
  });

  const activateKill = useMutation({
    mutationFn: (reason: string) => api.activateKillSwitch(reason),
    onSuccess: () => {
      toast.success("Kill switch activated");
      queryClient.invalidateQueries({ queryKey: ["safety-status"] });
    },
    onError: () => toast.error("Failed to activate kill switch"),
  });

  const resetKill = useMutation({
    mutationFn: () => api.resetKillSwitch(),
    onSuccess: () => {
      toast.success("Kill switch reset");
      queryClient.invalidateQueries({ queryKey: ["safety-status"] });
    },
    onError: () => toast.error("Failed to reset kill switch"),
  });

  const saveBudget = useMutation({
    mutationFn: () => api.upsertSpawnBudget(newBudget),
    onSuccess: () => {
      toast.success("Spawn budget saved");
      queryClient.invalidateQueries({ queryKey: ["safety-status"] });
    },
    onError: () => toast.error("Failed to save spawn budget"),
  });

  const budgets: SpawnBudget[] = useMemo(() => safety?.budgets || [], [safety]);

  if (!user?.is_admin) {
    return (
      <div className="space-y-4">
        <h1 className="text-3xl font-bold text-white flex items-center gap-2">
          <ShieldAlert className="w-7 h-7 text-emerald-500" />
          Safety Board
        </h1>
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="py-8 text-center text-zinc-400">
            Admin access required to view orchestrator safety controls.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-emerald-500" />
            Safety Board
          </h1>
          <p className="text-zinc-400">
            Spawn budgets, kill switch state, and orchestrator readiness.
          </p>
        </div>
        <Button
          variant="outline"
          className="border-zinc-700 text-zinc-200 hover:bg-zinc-800"
          onClick={() => queryClient.invalidateQueries({ queryKey: ["safety-status"] })}
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
        </div>
      ) : isError ? (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="py-6 text-center text-zinc-400">
            {String((error as any)?.response?.data?.detail || "Unable to load safety status")}
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase text-zinc-500">Kill switch</p>
                  <p className="text-xl font-bold text-white">
                    {safety?.kill_switch_active ? "ACTIVE" : "Inactive"}
                  </p>
                  <p className="text-xs text-zinc-500">
                    Orchestrator enabled: {safety?.orchestrator_enabled ? "yes" : "no"}
                  </p>
                </div>
                <Badge
                  variant="outline"
                  className={
                    safety?.kill_switch_active
                      ? "bg-red-500/10 text-red-400 border-red-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  }
                >
                  {safety?.kill_switch_active ? "STOPPED" : "RUNNING"}
                </Badge>
              </CardContent>
              <CardContent className="pt-0 pb-4 flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={activateKill.isPending || safety?.kill_switch_active}
                  onClick={() => activateKill.mutate("Manual activation from dashboard")}
                  className="border-red-500/40 text-red-400 hover:bg-red-500/10"
                >
                  <Power className="w-4 h-4 mr-2" />
                  Activate
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={resetKill.isPending || !safety?.kill_switch_active}
                  onClick={() => resetKill.mutate()}
                  className="border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/10"
                >
                  <ShieldCheck className="w-4 h-4 mr-2" />
                  Reset
                </Button>
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <p className="text-xs uppercase text-zinc-500">Spawn budgets</p>
                <p className="text-2xl font-bold text-white">{budgets.length}</p>
                <p className="text-xs text-zinc-500">Limits per scope/time window</p>
              </CardContent>
            </Card>

            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="p-4">
                <p className="text-xs uppercase text-zinc-500">Violations</p>
                <p className="text-2xl font-bold text-white">
                  {budgets.reduce((acc, b) => acc + (b.violations?.length || 0), 0)}
                </p>
                <p className="text-xs text-zinc-500">Recent budget violation attempts</p>
              </CardContent>
            </Card>
          </div>

          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-white">Budgets</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {budgets.length === 0 ? (
                <p className="text-sm text-zinc-500">No budgets configured.</p>
              ) : (
                budgets.map((budget) => (
                  <div
                    key={budget.budget_id}
                    className="border border-zinc-800 rounded-lg p-3 bg-zinc-950/50 flex flex-col gap-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                          {budget.scope_type}
                        </Badge>
                        {budget.agent_type_filter && (
                          <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                            {budget.agent_type_filter}
                          </Badge>
                        )}
                      </div>
                      <Badge variant="outline" className="bg-zinc-800 text-zinc-300 border-zinc-700">
                        {budget.current_spawns ?? 0}/{budget.max_spawns} {budget.time_window?.toLowerCase() || "window"}
                      </Badge>
                    </div>
                    <p className="text-xs text-zinc-500">
                      Action: {budget.action_on_exceed || "BLOCK"} · Cooldown:{" "}
                      {budget.cooldown_minutes ?? 0}m
                    </p>
                    {budget.violations && budget.violations.length > 0 && (
                      <p className="text-xs text-amber-400">
                        {budget.violations.length} violation(s) recorded
                      </p>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <AlertOctagon className="w-5 h-5 text-amber-500" />
                Add / update budget
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Select
                  value={newBudget.scope_type}
                  onValueChange={(v) => setNewBudget((prev) => ({ ...prev, scope_type: v }))}
                >
                  <SelectTrigger className="bg-zinc-900 border-zinc-800 text-zinc-200">
                    <SelectValue placeholder="Scope" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    {["GLOBAL", "AGENT_TYPE", "USER_INITIATED"].map((scope) => (
                      <SelectItem key={scope} value={scope} className="text-zinc-200">
                        {scope}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Input
                  placeholder="Agent type filter (optional)"
                  className="bg-zinc-900 border-zinc-800 text-white"
                  value={newBudget.agent_type_filter}
                  onChange={(e) => setNewBudget((prev) => ({ ...prev, agent_type_filter: e.target.value }))}
                />
                <Input
                  type="number"
                  min={1}
                  placeholder="Max spawns"
                  className="bg-zinc-900 border-zinc-800 text-white"
                  value={newBudget.max_spawns}
                  onChange={(e) => setNewBudget((prev) => ({ ...prev, max_spawns: Number(e.target.value) }))}
                />
                <Input
                  type="number"
                  min={0}
                  placeholder="Cooldown minutes"
                  className="bg-zinc-900 border-zinc-800 text-white"
                  value={newBudget.cooldown_minutes}
                  onChange={(e) =>
                    setNewBudget((prev) => ({ ...prev, cooldown_minutes: Number(e.target.value) }))
                  }
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Select
                  value={newBudget.time_window}
                  onValueChange={(v) => setNewBudget((prev) => ({ ...prev, time_window: v }))}
                >
                  <SelectTrigger className="bg-zinc-900 border-zinc-800 text-zinc-200">
                    <SelectValue placeholder="Window" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    {["DAILY", "HOURLY", "WEEKLY"].map((scope) => (
                      <SelectItem key={scope} value={scope} className="text-zinc-200">
                        {scope}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select
                  value={newBudget.action_on_exceed}
                  onValueChange={(v) => setNewBudget((prev) => ({ ...prev, action_on_exceed: v }))}
                >
                  <SelectTrigger className="bg-zinc-900 border-zinc-800 text-zinc-200">
                    <SelectValue placeholder="Action" />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    {["BLOCK", "WARN", "ALLOW_WITH_APPROVAL"].map((scope) => (
                      <SelectItem key={scope} value={scope} className="text-zinc-200">
                        {scope}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                onClick={() => saveBudget.mutate()}
                disabled={saveBudget.isPending}
                className="bg-emerald-500 hover:bg-emerald-600 text-black"
              >
                {saveBudget.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Save className="w-4 h-4 mr-2" />
                )}
                Save budget
              </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

