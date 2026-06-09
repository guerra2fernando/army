"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Task, TaskStatus } from "@/types/api";
import {
  Briefcase,
  Search,
  MapPin,
  Plus,
  RefreshCw,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Building2,
  ExternalLink,
  Sparkles,
  Globe,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const EXPERIENCE_LEVELS = ["Entry", "Mid", "Senior", "Lead", "Principal"];
const REMOTE_OPTIONS = ["Remote", "Hybrid", "On-site", "Any"];

type JobSearchResult = {
  jobs_found?: number;
  high_matches?: number;
  drafts_created?: number;
  jobs?: Array<Record<string, unknown>>;
  message?: string;
  output_path?: string;
};

type TaskResultEnvelope = {
  data?: JobSearchResult;
  error?: string | null;
  success?: boolean;
};

export default function JobsPage() {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: jobTasks, isLoading } = useQuery({
    queryKey: ["job-tasks"],
    queryFn: () => api.getTasks({ agent_target: "JOB_HUNTER", limit: 100 }),
    refetchInterval: 3000,
  });

  const createJobTaskMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.createTask({
        agent_target: "JOB_HUNTER",
        payload,
        priority: 5,
      }),
    onSuccess: (createdTask) => {
      queryClient.setQueryData<Task[]>(["job-tasks"], (current) => {
        const existing = current || [];
        const deduped = existing.filter((task) => task.task_id !== createdTask.task_id);
        return [createdTask, ...deduped].sort(
          (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
        );
      });
      queryClient.invalidateQueries({ queryKey: ["job-tasks"] });
      setDialogOpen(false);
    },
  });

  const sortedTasks = [...(jobTasks || [])].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
  );
  const pendingTasks = sortedTasks.filter(
    (t) => t.status === "PENDING" || t.status === "PICKED_UP" || t.status === "IN_PROGRESS"
  );
  const completedTasks = sortedTasks.filter((t) => t.status === "COMPLETED");
  const latestCompletedTask = completedTasks[0];
  const latestResult = getJobSearchResult(latestCompletedTask);
  const latestJobs = latestResult?.jobs || [];

  const totalJobsFound = completedTasks.reduce((acc, task) => {
    const result = getJobSearchResult(task);
    return acc + (result?.jobs_found || 0);
  }, 0);

  const totalDraftsReady = completedTasks.reduce((acc, task) => {
    const result = getJobSearchResult(task);
    return acc + (result?.drafts_created || 0);
  }, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Job Hunter</h1>
          <p className="text-zinc-400">Autonomous job search and application drafting</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ["job-tasks"] })}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800 hover:text-white"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <CreateJobSearchDialog
            open={dialogOpen}
            onOpenChange={setDialogOpen}
            onSubmit={(data) => createJobTaskMutation.mutate(data)}
            isLoading={createJobTaskMutation.isPending}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Active Searches" value={pendingTasks.length} icon={Search} color="text-blue-500" />
        <StatCard title="Jobs Found" value={totalJobsFound} icon={Building2} color="text-emerald-500" />
        <StatCard title="Drafts Ready" value={totalDraftsReady} icon={FileText} color="text-amber-500" />
        <StatCard title="Completed Searches" value={completedTasks.length} icon={CheckCircle} color="text-emerald-500" />
      </div>

      <Card className="bg-gradient-to-r from-blue-500/10 via-blue-500/5 to-transparent border-blue-500/20">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-full bg-blue-500/10">
                <Sparkles className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">Quick Search</h3>
                <p className="text-zinc-400">Start a job search with default parameters</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => createJobTaskMutation.mutate({
                  action: "search",
                  roles: ["Python Developer", "Backend Engineer"],
                  locations: ["Remote"],
                  experience: "Mid",
                })}
                disabled={createJobTaskMutation.isPending}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                Python Jobs
              </Button>
              <Button
                variant="outline"
                onClick={() => createJobTaskMutation.mutate({
                  action: "search",
                  roles: ["Growth", "Growth Marketing"],
                  locations: ["Remote"],
                  experience: "Lead",
                })}
                disabled={createJobTaskMutation.isPending}
                className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
              >
                Growth Jobs
              </Button>
              <Button disabled className="bg-blue-500 hover:bg-blue-600 text-white font-semibold">
                <FileText className="w-4 h-4 mr-2" />
                Draft Applications Soon
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Globe className="w-5 h-5 text-cyan-500" />
            Latest Job Results
          </CardTitle>
          <CardDescription className="text-zinc-400">
            Openings found in the most recent completed search
          </CardDescription>
        </CardHeader>
        <CardContent>
          {latestJobs.length > 0 ? (
            <div className="space-y-3">
              {latestJobs.slice(0, 10).map((job, index) => (
                <JobResultCard key={String(job.url || index)} job={job} />
              ))}
            </div>
          ) : latestCompletedTask ? (
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4 text-sm text-zinc-400">
              {latestResult?.message || "The latest completed search did not include parsed jobs."}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-500">No completed searches yet</div>
          )}
        </CardContent>
      </Card>

      {pendingTasks.length > 0 && (
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
              Active Searches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingTasks.map((task) => (
                <JobTaskRow key={task.task_id} task={task} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-white">
            <Briefcase className="w-5 h-5 text-emerald-500" />
            Search History
          </CardTitle>
          <CardDescription className="text-zinc-400">
            Recent Job Hunter tasks and result counts
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
            </div>
          ) : sortedTasks.length > 0 ? (
            <div className="space-y-3">
              {sortedTasks.slice(0, 20).map((task) => (
                <JobTaskRow key={task.task_id} task={task} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <Briefcase className="w-12 h-12 mx-auto text-zinc-600 mb-4" />
              <h3 className="text-lg font-medium text-zinc-300">No job searches yet</h3>
              <p className="text-zinc-500 mt-1">
                Start a job search to find opportunities that match your profile
              </p>
              <Button
                onClick={() => setDialogOpen(true)}
                className="mt-4 bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
              >
                <Plus className="w-4 h-4 mr-2" />
                Start Job Search
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <Icon className={`w-8 h-8 ${color}`} />
          <div>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-sm text-zinc-500">{title}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function JobTaskRow({ task }: { task: Task }) {
  const result = getJobSearchResult(task);
  const payload = (task.payload || {}) as Record<string, unknown>;
  const jobsFound = result?.jobs_found;
  const roles = Array.isArray(payload.roles)
    ? payload.roles.filter((role): role is string => typeof role === "string" && role.trim().length > 0)
    : [];
  const locations = Array.isArray(payload.locations)
    ? payload.locations.filter((location): location is string => typeof location === "string" && location.trim().length > 0)
    : [];
  const searchSummary = [roles.slice(0, 2).join(", "), locations.slice(0, 2).join(", ")]
    .filter(Boolean)
    .join(" | ");

  const statusConfig: Partial<Record<TaskStatus, { icon: React.ElementType; color: string; bg: string }>> = {
    PENDING: { icon: Clock, color: "text-amber-500", bg: "bg-amber-500/10" },
    PICKED_UP: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-500/10" },
    IN_PROGRESS: { icon: Loader2, color: "text-blue-500", bg: "bg-blue-500/10" },
    COMPLETED: { icon: CheckCircle, color: "text-emerald-500", bg: "bg-emerald-500/10" },
    FAILED: { icon: XCircle, color: "text-red-500", bg: "bg-red-500/10" },
    CANCELLED: { icon: XCircle, color: "text-zinc-500", bg: "bg-zinc-500/10" },
  };

  const config = statusConfig[task.status] || statusConfig.PENDING!;
  const StatusIcon = config.icon;

  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50 hover:bg-zinc-800 transition-colors">
      <div className="flex items-center gap-4">
        <div className={`p-2 rounded-lg ${config.bg}`}>
          <StatusIcon
            className={`w-5 h-5 ${config.color} ${
              task.status === "IN_PROGRESS" || task.status === "PICKED_UP" ? "animate-spin" : ""
            }`}
          />
        </div>
        <div>
          <p className="font-medium text-white">
            {payload.action === "search" ? "Job Search" : "Job Task"}
          </p>
          {searchSummary && (
            <p className="text-sm text-zinc-400">{searchSummary}</p>
          )}
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <span>{new Date(task.created_at).toLocaleString()}</span>
            <span>|</span>
            <span className="font-mono text-xs uppercase text-zinc-600">{task.task_id.slice(0, 8)}</span>
            {typeof jobsFound === "number" && (
              <>
                <span>|</span>
                <span className="text-emerald-500">{jobsFound} jobs found</span>
              </>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="outline" className={`${config.bg} ${config.color} border-transparent`}>
          {task.status}
        </Badge>
      </div>
    </div>
  );
}

function JobResultCard({ job }: { job: Record<string, unknown> }) {
  const title = String(job.title || "Untitled job");
  const company = String(job.company || "Unknown company");
  const location = String(job.location || "Remote");
  const url = typeof job.url === "string" ? job.url : null;
  const matchScore = typeof job.match_score === "number" ? job.match_score : null;

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-800/40 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-semibold text-white">{title}</p>
          <p className="text-sm text-zinc-400">{company}</p>
          <p className="text-sm text-zinc-500">{location}</p>
        </div>
        <div className="flex items-center gap-2">
          {matchScore !== null && (
            <Badge variant="outline" className="border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
              Match {Math.round(matchScore)}%
            </Badge>
          )}
          {url && (
            <Button asChild variant="ghost" size="sm" className="text-zinc-300 hover:text-white">
              <a href={url} target="_blank" rel="noreferrer">
                <ExternalLink className="w-4 h-4" />
              </a>
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function getJobSearchResult(task?: Task): JobSearchResult | undefined {
  if (!task?.result || typeof task.result === "string") {
    return undefined;
  }

  const envelope = task.result as TaskResultEnvelope;
  if (envelope.data && typeof envelope.data === "object") {
    return envelope.data;
  }

  return task.result as JobSearchResult;
}

function CreateJobSearchDialog({
  open,
  onOpenChange,
  onSubmit,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: Record<string, unknown>) => void;
  isLoading: boolean;
}) {
  const [titles, setTitles] = useState("Python Engineer, Backend Engineer");
  const [locations, setLocations] = useState("Remote");
  const [experience, setExperience] = useState("Mid");
  const [remote, setRemote] = useState("Any");
  const [keywords, setKeywords] = useState("");

  const handleSubmit = () => {
    onSubmit({
      action: "search",
      roles: titles.split(",").map((t) => t.trim()).filter(Boolean),
      locations: locations.split(",").map((l) => l.trim()).filter(Boolean),
      experience,
      remote_preference: remote,
      keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean),
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold">
          <Plus className="w-4 h-4 mr-2" />
          New Search
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle className="text-white">Create Job Search</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Configure your search terms. The Job Hunter will find positions and rank them.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label className="text-zinc-300">Job Titles (comma-separated)</Label>
            <Input
              value={titles}
              onChange={(e) => setTitles(e.target.value)}
              placeholder="Python Engineer, Backend Engineer"
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
            />
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-300 flex items-center gap-2">
              <MapPin className="w-4 h-4" />
              Locations (comma-separated)
            </Label>
            <Input
              value={locations}
              onChange={(e) => setLocations(e.target.value)}
              placeholder="Remote, Berlin, London"
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-zinc-300">Experience Level</Label>
              <Select value={experience} onValueChange={setExperience}>
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-zinc-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-800">
                  {EXPERIENCE_LEVELS.map((level) => (
                    <SelectItem key={level} value={level} className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      {level}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-zinc-300">Remote Preference</Label>
              <Select value={remote} onValueChange={setRemote}>
                <SelectTrigger className="bg-zinc-800 border-zinc-700 text-zinc-300">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-800">
                  {REMOTE_OPTIONS.map((option) => (
                    <SelectItem key={option} value={option} className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="text-zinc-300">Keywords (optional, comma-separated)</Label>
            <Input
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="FastAPI, PostgreSQL, Docker"
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || !titles.trim()}
            className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
          >
            {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Start Search
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
