"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { FollowupPlan, ReviewQueueItem, SendIntent } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertTriangle, CheckCircle2, Loader2, PauseCircle, PlayCircle, Send, Shield, Trash2, XCircle } from "lucide-react";
import { toast } from "sonner";

const ALL = "__all__";

function formatDateTime(value?: string | null) {
  if (!value) {
    return "Not scheduled";
  }
  return new Date(value).toLocaleString();
}

export default function ApprovalsPage() {
  const queryClient = useQueryClient();
  const [lane, setLane] = useState<string>(ALL);
  const [status, setStatus] = useState<string>("PENDING");
  const [persona, setPersona] = useState<string>(ALL);
  const [channel, setChannel] = useState<string>(ALL);
  const [company, setCompany] = useState("");

  const params = {
    status: status === ALL ? undefined : status,
    lane: lane === ALL ? undefined : lane,
    target_persona: persona === ALL ? undefined : persona,
    recommended_channel: channel === ALL ? undefined : channel,
    company: company || undefined,
    limit: 100,
  };

  const { data: reviewItems = [], isLoading } = useQuery({
    queryKey: ["commercial-review-items", params],
    queryFn: () => api.listReviewItems(params),
    refetchInterval: 4000,
  });

  const { data: sendIntents = [] } = useQuery({
    queryKey: ["commercial-send-intents"],
    queryFn: () => api.listSendIntents(100),
    refetchInterval: 4000,
  });

  const { data: followupPlans = [] } = useQuery({
    queryKey: ["commercial-followups"],
    queryFn: () => api.listFollowupPlans(100),
    refetchInterval: 4000,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["commercial-review-items"] });
    queryClient.invalidateQueries({ queryKey: ["commercial-send-intents"] });
    queryClient.invalidateQueries({ queryKey: ["commercial-followups"] });
  };

  const approve = useMutation({
    mutationFn: (id: string) => api.approveReviewItem(id),
    onSuccess: () => {
      toast.success("Review item processed");
      refresh();
    },
    onError: () => toast.error("Failed to approve review item"),
  });

  const reject = useMutation({
    mutationFn: (id: string) => api.rejectReviewItem(id, "Rejected from dashboard"),
    onSuccess: () => {
      toast.success("Review item rejected");
      refresh();
    },
    onError: () => toast.error("Failed to reject review item"),
  });

  const archive = useMutation({
    mutationFn: (id: string) => api.archiveReviewItem(id, "Archived from dashboard"),
    onSuccess: () => {
      toast.success("Review item archived");
      refresh();
    },
    onError: () => toast.error("Failed to archive review item"),
  });

  const pause = useMutation({
    mutationFn: (id: string) => api.pauseReviewFollowup(id, "Paused from dashboard"),
    onSuccess: () => {
      toast.success("Follow-up paused");
      refresh();
    },
    onError: () => toast.error("Failed to pause follow-up"),
  });

  const resume = useMutation({
    mutationFn: (id: string) => api.resumeReviewFollowup(id, "Resumed from dashboard"),
    onSuccess: () => {
      toast.success("Follow-up resumed");
      refresh();
    },
    onError: () => toast.error("Failed to resume follow-up"),
  });

  const cancelFollowup = useMutation({
    mutationFn: (id: string) => api.cancelReviewFollowup(id, "Cancelled from dashboard"),
    onSuccess: () => {
      toast.success("Follow-up cancelled");
      refresh();
    },
    onError: () => toast.error("Failed to cancel follow-up"),
  });

  const dispatch = useMutation({
    mutationFn: (id: string) => api.dispatchSendIntent(id),
    onSuccess: () => {
      toast.success("Send dispatched");
      refresh();
    },
    onError: () => toast.error("Failed to dispatch send"),
  });

  const pending = useMemo(
    () => reviewItems.filter((item) => item.status === "PENDING" || item.status === "PAUSED" || item.status === "BLOCKED"),
    [reviewItems],
  );
  const readyToSend = useMemo(
    () => sendIntents.filter((item) => item.status === "READY" || item.status === "FAILED"),
    [sendIntents],
  );
  const loadingAction =
    approve.isPending || reject.isPending || archive.isPending || pause.isPending || resume.isPending || cancelFollowup.isPending;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-3xl font-bold text-white">
            <Shield className="h-7 w-7 text-emerald-500" />
            Commercial Approvals
          </h1>
          <p className="text-zinc-400">
            Review jobs and commercial outreach, then dispatch approved sends conservatively.
          </p>
        </div>
      </div>

      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <CardTitle className="text-white">Queue filters</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-5">
          <FilterSelect label="Lane" value={lane} onValueChange={setLane} options={["JOBS", "LENQUANT", "LENXYS", "SERVICES", "TRADING"]} />
          <FilterSelect label="Status" value={status} onValueChange={setStatus} options={["PENDING", "BLOCKED", "PAUSED", "APPROVED", "REJECTED", "REROUTED", "ARCHIVED"]} />
          <FilterSelect label="Persona" value={persona} onValueChange={setPersona} options={["RECRUITER", "HIRING_MANAGER", "FOUNDER", "CEO", "COO", "PORTFOLIO_MANAGER", "HEAD_OF_GROWTH"]} />
          <FilterSelect label="Channel" value={channel} onValueChange={setChannel} options={["EMAIL", "LINKEDIN_DM", "LINKEDIN_CONNECT", "MANUAL"]} />
          <div className="space-y-2">
            <Label className="text-zinc-300">Company</Label>
            <Input
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="Filter by company"
              className="border-zinc-800 bg-zinc-950 text-zinc-200"
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <CardTitle className="text-white">Pending review queue</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="h-6 w-6 animate-spin text-zinc-500" />
            </div>
          ) : pending.length === 0 ? (
            <p className="text-sm text-zinc-500">No matching review items right now.</p>
          ) : (
            <div className="space-y-4">
              {pending.map((item) => (
                <ReviewCard
                  key={item.review_id}
                  item={item}
                  plan={followupPlans.find((plan) => plan.followup_id === item.followup_plan_id)}
                  onApprove={() => approve.mutate(item.review_id)}
                  onReject={() => reject.mutate(item.review_id)}
                  onArchive={() => archive.mutate(item.review_id)}
                  onPause={() => pause.mutate(item.review_id)}
                  onResume={() => resume.mutate(item.review_id)}
                  onCancelFollowup={() => cancelFollowup.mutate(item.review_id)}
                  loading={loadingAction}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-zinc-800 bg-zinc-900/50">
        <CardHeader>
          <CardTitle className="text-white">Ready-to-send</CardTitle>
        </CardHeader>
        <CardContent>
          {readyToSend.length === 0 ? (
            <p className="text-sm text-zinc-500">No send intents are ready yet.</p>
          ) : (
            <div className="space-y-3">
              {readyToSend.map((intent) => (
                <SendIntentCard key={intent.send_intent_id} intent={intent} onDispatch={() => dispatch.mutate(intent.send_intent_id)} loading={dispatch.isPending} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onValueChange,
  options,
}: {
  label: string;
  value: string;
  onValueChange: (value: string) => void;
  options: string[];
}) {
  return (
    <div className="space-y-2">
      <Label className="text-zinc-300">{label}</Label>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger className="border-zinc-800 bg-zinc-950 text-zinc-200">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>All {label.toLowerCase()}s</SelectItem>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option.replaceAll("_", " ")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function ReviewCard({
  item,
  plan,
  onApprove,
  onReject,
  onArchive,
  onPause,
  onResume,
  onCancelFollowup,
  loading,
}: {
  item: ReviewQueueItem;
  plan?: FollowupPlan;
  onApprove: () => void;
  onReject: () => void;
  onArchive: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancelFollowup: () => void;
  loading: boolean;
}) {
  const blockedReasons = item.blocked_reasons || [];
  const nextAction = item.next_action_at || plan?.next_action_at;

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-300">
              {item.status}
            </Badge>
            {item.review_kind === "FOLLOWUP" ? (
              <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                Follow-up #{item.followup_step ?? "?"}
              </Badge>
            ) : null}
            <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-300">
              {item.lane}
            </Badge>
            <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-300">
              {item.target_persona}
            </Badge>
            <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-300">
              {Math.round(item.confidence * 100)}% fit
            </Badge>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              {item.primary_draft.subject || item.recommended_next_step}
            </h2>
            <p className="text-sm text-zinc-400">{item.source_url}</p>
            <p className="text-sm text-zinc-500">
              Follow-up: {item.followup_status || plan?.status || "NONE"} · next {formatDateTime(nextAction)}
            </p>
          </div>
          <p className="whitespace-pre-wrap text-sm text-zinc-300">{item.primary_draft.body}</p>
          {blockedReasons.length > 0 ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
              <div className="flex items-center gap-2 text-red-300">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">Blocked by guardrails</span>
              </div>
              <div className="mt-2 space-y-1">
                {blockedReasons.map((reason, index) => (
                  <p key={`${item.review_id}-blocked-${index}`} className="text-sm text-red-200">
                    {reason}
                  </p>
                ))}
              </div>
            </div>
          ) : null}
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Rationale</p>
              <div className="mt-2 space-y-1">
                {item.rationale.map((reason, index) => (
                  <p key={`${item.review_id}-reason-${index}`} className="text-sm text-zinc-300">
                    {reason}
                  </p>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
              <p className="text-xs uppercase tracking-wide text-zinc-500">Follow-ups</p>
              <div className="mt-2 space-y-2">
                {item.followups.length === 0 ? (
                  <p className="text-sm text-zinc-500">No follow-ups configured.</p>
                ) : (
                  item.followups.map((draft, index) => (
                    <div key={`${item.review_id}-followup-${index}`} className="text-sm text-zinc-300">
                      <span className="text-zinc-500">Day {draft.delay_days}:</span> {draft.body}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 lg:w-44 lg:flex-col">
          <Button onClick={onApprove} disabled={loading} className="bg-emerald-500 text-black hover:bg-emerald-600">
            <CheckCircle2 className="mr-2 h-4 w-4" />
            Approve
          </Button>
          <Button onClick={onReject} disabled={loading} variant="outline" className="border-red-500/40 text-red-400 hover:bg-red-500/10">
            <XCircle className="mr-2 h-4 w-4" />
            Reject
          </Button>
          <Button onClick={onPause} disabled={loading} variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <PauseCircle className="mr-2 h-4 w-4" />
            Pause
          </Button>
          <Button onClick={onResume} disabled={loading} variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <PlayCircle className="mr-2 h-4 w-4" />
            Resume
          </Button>
          <Button onClick={onCancelFollowup} disabled={loading} variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <Trash2 className="mr-2 h-4 w-4" />
            Cancel FU
          </Button>
          <Button onClick={onArchive} disabled={loading} variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            <Trash2 className="mr-2 h-4 w-4" />
            Archive
          </Button>
        </div>
      </div>
    </div>
  );
}

function SendIntentCard({
  intent,
  onDispatch,
  loading,
}: {
  intent: SendIntent;
  onDispatch: () => void;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              {intent.status}
            </Badge>
            {intent.is_followup ? (
              <Badge variant="outline" className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                Follow-up #{intent.followup_step ?? "?"}
              </Badge>
            ) : null}
            <span className="font-medium text-white">{intent.channel}</span>
          </div>
          <p className="text-sm text-zinc-400">Review item: {intent.review_id}</p>
          {intent.blocked_reasons?.map((reason, index) => (
            <p key={`${intent.send_intent_id}-reason-${index}`} className="text-sm text-red-400">
              {reason}
            </p>
          ))}
          {intent.last_error ? <p className="text-sm text-red-400">{intent.last_error}</p> : null}
        </div>
        <Button onClick={onDispatch} disabled={loading || (intent.blocked_reasons?.length ?? 0) > 0} className="bg-emerald-500 text-black hover:bg-emerald-600">
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
          Dispatch
        </Button>
      </div>
    </div>
  );
}
