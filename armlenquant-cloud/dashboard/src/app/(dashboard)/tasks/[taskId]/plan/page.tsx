"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  User,
  Zap,
  Code,
  Database,
  Globe,
  Check,
  X,
  Edit,
  PlayCircle,
  PauseCircle,
  RotateCcw,
  ChevronRight,
  DollarSign,
  Calendar,
  Target,
  ListChecks,
  Save,
  Settings,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { formatDateInTbilisi } from "@/lib/utils";
import { useState } from "react";
import { toast } from "sonner";

interface MasterPlan {
  plan_id: string;
  task_id: string;
  project_name: string;
  scope: "FRONTEND" | "BACKEND" | "FULLSTACK";
  tech_stack: {
    explicit_preferences: Record<string, string>;
    recommended_stack: {
      frontend: string;
      backend: string;
      infrastructure: string;
    };
    alternatives: any[];
  };
  phases: Array<{
    id: string;
    name: string;
    description: string;
    estimated_duration: string;
    deliverables: string[];
    success_criteria: string[];
    dependencies: string[];
  }>;
  estimated_hours: number;
  risks: string[];
  assumptions: string[];
  created_at: string;
  approved_at?: string;
  approved_by?: string;
}

export default function TaskPlanPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const taskId = params.taskId as string;
  const [rejectionReason, setRejectionReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState<MasterPlan | null>(null);

  const { data: plan, isLoading, error } = useQuery({
    queryKey: ["task-plan", taskId],
    queryFn: async () => {
      const response = await api.get(`/api/v1/tasks/${taskId}/plan`);
      return response.data as MasterPlan;
    },
    enabled: !!taskId,
  });

  const approveMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/tasks/${taskId}/plans/${plan?.plan_id}/approve`);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Plan approved successfully");
      queryClient.invalidateQueries({ queryKey: ["task-plan", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      router.push(`/tasks/${taskId}`);
    },
    onError: (error: any) => {
      toast.error(`Failed to approve plan: ${error.message}`);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/tasks/${taskId}/plans/${plan?.plan_id}/reject`, {
        rejection_reason: rejectionReason,
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success("Plan rejected successfully");
      queryClient.invalidateQueries({ queryKey: ["task-plan", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      router.push(`/tasks/${taskId}`);
    },
    onError: (error: any) => {
      toast.error(`Failed to reject plan: ${error.message}`);
    },
  });

  const startExecutionMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post(`/api/v1/tasks/${taskId}/start-execution`);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Execution started successfully");
      queryClient.invalidateQueries({ queryKey: ["task-plan", taskId] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      router.push(`/tasks/${taskId}`);
    },
    onError: (error: any) => {
      toast.error(`Failed to start execution: ${error.message}`);
    },
  });

  const modifyPlanMutation = useMutation({
    mutationFn: async (modifications: any) => {
      return await api.modifyPlan(taskId, plan!.plan_id, modifications);
    },
    onSuccess: () => {
      toast.success("Plan modified successfully");
      queryClient.invalidateQueries({ queryKey: ["task-plan", taskId] });
      setIsEditing(false);
      setEditedPlan(null);
    },
    onError: (error: any) => {
      toast.error(`Failed to modify plan: ${error.message}`);
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Task
          </Button>
        </div>
        <div className="text-center py-12">
          <Clock className="w-8 h-8 animate-spin mx-auto text-zinc-500" />
          <p className="text-zinc-400 mt-4">Loading master plan...</p>
        </div>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Task
          </Button>
        </div>
        <div className="text-center py-12">
          <AlertCircle className="w-8 h-8 mx-auto text-red-500" />
          <p className="text-zinc-400 mt-4">Failed to load master plan</p>
        </div>
      </div>
    );
  }

  const activePlan = editedPlan ?? plan;

  const getScopeIcon = (scope: string) => {
    switch (scope) {
      case "FRONTEND":
        return <Globe className="w-5 h-5 text-blue-500" />;
      case "BACKEND":
        return <Database className="w-5 h-5 text-green-500" />;
      case "FULLSTACK":
        return <Code className="w-5 h-5 text-purple-500" />;
      default:
        return <Code className="w-5 h-5 text-gray-500" />;
    }
  };

  const getScopeColor = (scope: string) => {
    switch (scope) {
      case "FRONTEND":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20";
      case "BACKEND":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "FULLSTACK":
        return "bg-purple-500/10 text-purple-500 border-purple-500/20";
      default:
        return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Task
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-white">Master Plan Review</h1>
            <p className="text-zinc-400">Project: {plan.project_name}</p>
            {isEditing && (
              <p className="text-blue-400 text-sm mt-1">
                ✏️ Editing mode: Modify scope and tech preferences before approving
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!plan.approved_at && (
            <>
              {!isEditing && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditing(true);
                    setEditedPlan(JSON.parse(JSON.stringify(plan)));
                  }}
                  className="border-blue-500/20 text-blue-400 hover:bg-blue-500/10"
                >
                  <Edit className="w-4 h-4 mr-2" />
                  Edit Plan
                </Button>
              )}
              {isEditing && (
                <>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setIsEditing(false);
                      setEditedPlan(null);
                    }}
                    disabled={modifyPlanMutation.isPending}
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={() => {
                      if (!editedPlan) {
                        return;
                      }
                      // Calculate what changed
                      const modifications: any = {};
                      if (editedPlan.scope !== plan.scope) modifications.scope = editedPlan.scope;
                      if (editedPlan.tech_stack?.explicit_preferences) {
                        modifications["tech_stack.explicit_preferences"] = editedPlan.tech_stack.explicit_preferences;
                      }
                      modifyPlanMutation.mutate(modifications);
                    }}
                    disabled={modifyPlanMutation.isPending}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {modifyPlanMutation.isPending ? "Saving..." : "Save Changes"}
                  </Button>
                </>
              )}
              <Button
                variant="outline"
                onClick={() => setShowRejectForm(true)}
                disabled={rejectMutation.isPending || isEditing}
              >
                <X className="w-4 h-4 mr-2" />
                Reject
              </Button>
              <Button
                onClick={() => approveMutation.mutate()}
                disabled={approveMutation.isPending || isEditing}
                className="bg-green-600 hover:bg-green-700"
              >
                <Check className="w-4 h-4 mr-2" />
                {approveMutation.isPending ? "Approving..." : "Approve Plan"}
              </Button>
            </>
          )}
          {plan.approved_at && (
            <Button
              onClick={() => startExecutionMutation.mutate()}
              disabled={startExecutionMutation.isPending}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <PlayCircle className="w-4 h-4 mr-2" />
              {startExecutionMutation.isPending ? "Starting..." : "Start Execution"}
            </Button>
          )}
        </div>
      </div>

      {/* Plan Status */}
      <Card className={`bg-zinc-900/50 border-zinc-800 ${isEditing ? 'ring-2 ring-blue-500/20' : ''}`}>
        <CardHeader>
          <CardTitle className="flex items-center gap-3">
            {getScopeIcon(isEditing ? activePlan.scope : plan.scope)}
            Plan Overview
            {isEditing && <Badge variant="outline" className="border-blue-500/20 text-blue-400 text-xs">EDITING</Badge>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Project Scope</p>
              {isEditing ? (
                <Select
                  value={activePlan.scope}
                  onValueChange={(value) => setEditedPlan((prev) => (prev ? { ...prev, scope: value as MasterPlan["scope"] } : prev))}
                >
                  <SelectTrigger className="w-32 bg-zinc-800 border-zinc-700 text-zinc-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    <SelectItem value="FRONTEND" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      FRONTEND
                    </SelectItem>
                    <SelectItem value="BACKEND" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      BACKEND
                    </SelectItem>
                    <SelectItem value="FULLSTACK" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      FULLSTACK
                    </SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <Badge variant="outline" className={getScopeColor(plan.scope)}>
                  {plan.scope}
                </Badge>
              )}
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Estimated Hours</p>
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-zinc-400" />
                <span className="text-white font-mono">{plan.estimated_hours}h</span>
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Development Phases</p>
              <div className="flex items-center gap-2">
                <ListChecks className="w-4 h-4 text-zinc-400" />
                <span className="text-white font-mono">{plan.phases.length}</span>
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-zinc-500">Status</p>
              <Badge
                variant="outline"
                className={
                  plan.approved_at
                    ? "border-green-500/20 text-green-400"
                    : "border-yellow-500/20 text-yellow-400"
                }
              >
                {plan.approved_at ? "Approved" : "Pending Approval"}
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tech Stack */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Technology Stack
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm text-zinc-500 mb-2">Recommended Stack</p>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-2 bg-zinc-950/30 rounded">
                  <span className="text-zinc-300">Frontend</span>
                  <Badge variant="outline" className="border-blue-500/20 text-blue-400">
                    {plan.tech_stack.recommended_stack.frontend}
                  </Badge>
                </div>
                <div className="flex justify-between items-center p-2 bg-zinc-950/30 rounded">
                  <span className="text-zinc-300">Backend</span>
                  <Badge variant="outline" className="border-green-500/20 text-green-400">
                    {plan.tech_stack.recommended_stack.backend}
                  </Badge>
                </div>
                <div className="flex justify-between items-center p-2 bg-zinc-950/30 rounded">
                  <span className="text-zinc-300">Infrastructure</span>
                  <Badge variant="outline" className="border-purple-500/20 text-purple-400">
                    {plan.tech_stack.recommended_stack.infrastructure}
                  </Badge>
                </div>
              </div>
            </div>

            {isEditing ? (
              <div>
                <p className="text-sm text-zinc-500 mb-2">Explicit Preferences</p>
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <Label className="text-xs text-zinc-400">Database</Label>
                      <Input
                        placeholder="e.g., mongodb, postgresql"
                        value={activePlan.tech_stack?.explicit_preferences?.database || ""}
                        onChange={(e) => {
                          const prefs = { ...(activePlan.tech_stack?.explicit_preferences || {}) };
                          if (e.target.value) {
                            prefs.database = e.target.value;
                          } else {
                            delete prefs.database;
                          }
                          setEditedPlan((prev) => (prev ? {
                            ...prev,
                            tech_stack: {
                              ...prev.tech_stack,
                              explicit_preferences: prefs
                            }
                          } : prev));
                        }}
                        className="bg-zinc-800 border-zinc-700 text-zinc-300 text-sm h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-zinc-400">Backend Framework</Label>
                      <Input
                        placeholder="e.g., fastapi, flask, django"
                        value={activePlan.tech_stack?.explicit_preferences?.backend_framework || ""}
                        onChange={(e) => {
                          const prefs = { ...(activePlan.tech_stack?.explicit_preferences || {}) };
                          if (e.target.value) {
                            prefs.backend_framework = e.target.value;
                          } else {
                            delete prefs.backend_framework;
                          }
                          setEditedPlan((prev) => (prev ? {
                            ...prev,
                            tech_stack: {
                              ...prev.tech_stack,
                              explicit_preferences: prefs
                            }
                          } : prev));
                        }}
                        className="bg-zinc-800 border-zinc-700 text-zinc-300 text-sm h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-zinc-400">Frontend Framework</Label>
                      <Input
                        placeholder="e.g., nextjs, react, vue"
                        value={activePlan.tech_stack?.explicit_preferences?.frontend_framework || ""}
                        onChange={(e) => {
                          const prefs = { ...(activePlan.tech_stack?.explicit_preferences || {}) };
                          if (e.target.value) {
                            prefs.frontend_framework = e.target.value;
                          } else {
                            delete prefs.frontend_framework;
                          }
                          setEditedPlan((prev) => (prev ? {
                            ...prev,
                            tech_stack: {
                              ...prev.tech_stack,
                              explicit_preferences: prefs
                            }
                          } : prev));
                        }}
                        className="bg-zinc-800 border-zinc-700 text-zinc-300 text-sm h-8"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-xs text-zinc-400">Language</Label>
                      <Input
                        placeholder="e.g., python, javascript, typescript"
                        value={activePlan.tech_stack?.explicit_preferences?.language || ""}
                        onChange={(e) => {
                          const prefs = { ...(activePlan.tech_stack?.explicit_preferences || {}) };
                          if (e.target.value) {
                            prefs.language = e.target.value;
                          } else {
                            delete prefs.language;
                          }
                          setEditedPlan((prev) => (prev ? {
                            ...prev,
                            tech_stack: {
                              ...prev.tech_stack,
                              explicit_preferences: prefs
                            }
                          } : prev));
                        }}
                        className="bg-zinc-800 border-zinc-700 text-zinc-300 text-sm h-8"
                      />
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              Object.keys(plan.tech_stack.explicit_preferences || {}).length > 0 && (
                <div>
                  <p className="text-sm text-zinc-500 mb-2">Explicit Preferences</p>
                  <div className="space-y-1">
                    {Object.entries(plan.tech_stack.explicit_preferences).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center text-sm">
                        <span className="text-zinc-400 capitalize">{key.replace('_', ' ')}</span>
                        <Badge variant="outline" className="border-yellow-500/20 text-yellow-400">
                          {value}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )
            )}
          </CardContent>
        </Card>

        {/* Project Phases */}
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Development Phases
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {plan.phases.map((phase, index) => (
                <div key={phase.id} className="border border-zinc-700 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-zinc-700 rounded-full flex items-center justify-center text-xs font-medium">
                        {index + 1}
                      </div>
                      <h3 className="font-medium text-white">{phase.name}</h3>
                    </div>
                    <Badge variant="outline" className="border-zinc-600 text-zinc-300">
                      {phase.estimated_duration}
                    </Badge>
                  </div>

                  <p className="text-sm text-zinc-400 mb-3">{phase.description}</p>

                  <div className="space-y-2">
                    <div>
                      <p className="text-xs text-zinc-500 mb-1">Deliverables</p>
                      <ul className="text-xs text-zinc-300 space-y-1">
                        {phase.deliverables.map((deliverable, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <Check className="w-3 h-3 text-green-500 mt-0.5 flex-shrink-0" />
                            {deliverable}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Risks and Assumptions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              Risks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {plan.risks.map((risk, index) => (
                <div key={index} className="flex items-start gap-2 p-2 bg-red-950/20 rounded">
                  <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-zinc-300">{risk}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              Assumptions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {plan.assumptions.map((assumption, index) => (
                <div key={index} className="flex items-start gap-2 p-2 bg-green-950/20 rounded">
                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-zinc-300">{assumption}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Rejection Form */}
      {showRejectForm && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="w-5 h-5 text-red-500" />
              Reject Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm text-zinc-500 block mb-2">
                Reason for rejection (optional)
              </label>
              <Textarea
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="Please provide feedback on why this plan doesn't meet your requirements..."
                className="bg-zinc-950 border-zinc-700"
                rows={4}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowRejectForm(false);
                  setRejectionReason("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => rejectMutation.mutate()}
                disabled={rejectMutation.isPending}
              >
                {rejectMutation.isPending ? "Rejecting..." : "Confirm Rejection"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
