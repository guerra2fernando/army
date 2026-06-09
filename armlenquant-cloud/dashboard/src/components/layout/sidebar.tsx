"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  ListTodo,
  TrendingUp,
  Briefcase,
  FolderKanban,
  Settings,
  Zap,
  GitBranch,
  ShieldCheck,
  PanelsTopLeft,
  Shield,
  CheckSquare,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Command Center", href: "/", icon: LayoutDashboard },
  { name: "Workflows", href: "/workflows", icon: GitBranch },
  { name: "Agents", href: "/agents", icon: Bot },
  { name: "Tasks", href: "/tasks", icon: ListTodo },
  { name: "Reliability", href: "/reliability", icon: ShieldCheck },
  { name: "Configs", href: "/configs", icon: PanelsTopLeft },
  { name: "Capabilities", href: "/capabilities", icon: Sparkles },
  { name: "Approvals", href: "/approvals", icon: CheckSquare },
  { name: "Security", href: "/security", icon: Shield },
  { name: "Safety", href: "/safety", icon: ShieldAlert },
  { name: "Crypto", href: "/crypto", icon: TrendingUp },
  { name: "Jobs", href: "/jobs", icon: Briefcase },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-800 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-zinc-800">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-black" />
          </div>
          <span className="text-xl font-bold text-white">ArmLenQuant</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navigation.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-emerald-500/10 text-emerald-500"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Settings */}
      <div className="p-4 border-t border-zinc-800">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          <Settings className="w-5 h-5" />
          Settings
        </Link>
      </div>
    </aside>
  );
}

