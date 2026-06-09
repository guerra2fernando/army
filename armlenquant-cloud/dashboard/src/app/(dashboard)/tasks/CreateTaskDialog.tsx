"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { AgentTarget } from "@/types/api";

const AGENT_OPTIONS: AgentTarget[] = [
  "ORCHESTRATOR",
  "CRYPTO_SENTINEL",
  "JOB_HUNTER",
  "IDEAS_MACHINE",
  "META_BUILDER",
];

interface CreateTaskDialogProps {
  onSubmit: (data: { agent_target: AgentTarget; payload: Record<string, unknown>; priority: number; recurring: boolean }) => void;
  isLoading: boolean;
}

export default function CreateTaskDialog({ onSubmit, isLoading }: CreateTaskDialogProps) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"natural" | "advanced">("natural");
  const [instruction, setInstruction] = useState("");
  const [agent, setAgent] = useState<AgentTarget>("ORCHESTRATOR");
  const [priority, setPriority] = useState(5);
  const [payload, setPayload] = useState("{}");
  const [recurring, setRecurring] = useState(false);

  const handleSubmit = () => {
    if (mode === "natural") {
      // Send to orchestrator with natural language instruction
      onSubmit({
        agent_target: "ORCHESTRATOR",
        payload: { instruction, action: "process" },
        priority,
        recurring,
      });
      setOpen(false);
      setInstruction("");
      setRecurring(false);
    } else {
      // Advanced mode with JSON payload
      try {
        const parsedPayload = JSON.parse(payload);
        onSubmit({ agent_target: agent, payload: parsedPayload, priority, recurring });
        setOpen(false);
        setRecurring(false);
      } catch {
        alert("Invalid JSON payload");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold">
          <Plus className="w-4 h-4 mr-2" />
          New Task
        </Button>
      </DialogTrigger>
      <DialogContent className="bg-zinc-900 border-zinc-800">
        <DialogHeader>
          <DialogTitle className="text-white">Create New Task</DialogTitle>
          <DialogDescription className="text-zinc-400">
            Tell the AI what you want to do - it will figure out the rest.
          </DialogDescription>
        </DialogHeader>

        {/* Mode Toggle */}
        <div className="flex gap-2 p-1 bg-zinc-800 rounded-lg">
          <button
            onClick={() => setMode("natural")}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              mode === "natural"
                ? "bg-emerald-500 text-black"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            💬 Natural Language
          </button>
          <button
            onClick={() => setMode("advanced")}
            className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              mode === "advanced"
                ? "bg-emerald-500 text-black"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            ⚙️ Advanced
          </button>
        </div>

        <div className="space-y-4 py-4">
          {mode === "natural" ? (
            <div className="space-y-2">
              <Label className="text-zinc-300">What do you want to do?</Label>
              <textarea
                className="w-full h-24 p-3 rounded-md bg-zinc-800 border border-zinc-700 text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g., Build a complete habit tracking app with streaks and gamification, Find Python developer jobs in London, Analyze Bitcoin price trends..."
              />
              <p className="text-xs text-zinc-500">
                For complete project generation (full apps with code), use phrases like "Build a complete..." or "Generate a full-stack...". The AI will create a detailed plan first for your approval before starting development.
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label className="text-zinc-300">Target Agent</Label>
                <Select value={agent} onValueChange={(v) => setAgent(v as AgentTarget)}>
                  <SelectTrigger className="bg-zinc-800 border-zinc-700 text-zinc-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    {AGENT_OPTIONS.map((a) => (
                      <SelectItem key={a} value={a} className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                        {a}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label className="text-zinc-300">Payload (JSON)</Label>
                <textarea
                  className="w-full h-32 p-3 rounded-md bg-zinc-800 border border-zinc-700 font-mono text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  value={payload}
                  onChange={(e) => setPayload(e.target.value)}
                  placeholder='{"action": "search"}'
                />
              </div>
            </>
          )}
          <div className="space-y-2">
            <Label className="text-zinc-300">Priority (1-10)</Label>
            <Input
              type="number"
              min={1}
              max={10}
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value))}
              className="bg-zinc-800 border-zinc-700 text-white"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-zinc-300">Recurring Task</Label>
              <p className="text-xs text-zinc-500">
                Automatically recreate when completed
              </p>
            </div>
            <Switch
              checked={recurring}
              onCheckedChange={setRecurring}
              className="data-[state=checked]:bg-emerald-500"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || (mode === "natural" && !instruction.trim())}
            className="bg-emerald-500 hover:bg-emerald-600 text-black"
          >
            {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {mode === "natural" ? "Send to AI" : "Create Task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}