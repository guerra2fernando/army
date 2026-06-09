"use client";

import { useState, type ReactNode } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Notification } from "@/types/api";
import {
  Bell,
  Search,
  User,
  LogOut,
  Settings,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  Briefcase,
  Bot,
  MessageCircle,
  Loader2,
  Send,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/hooks/use-auth";
import Link from "next/link";

export function Header() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [showNotifications, setShowNotifications] = useState(false);

  const { data: notifications, isLoading: notificationsLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api.getNotifications({ limit: 10 }),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: false,
  });

  const { data: telegramStatus } = useQuery({
    queryKey: ["telegram-status"],
    queryFn: () => api.getTelegramStatus(),
    retry: false,
  });

  const testTelegramMutation = useMutation({
    mutationFn: () => api.testTelegramNotification(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const unreadCount = notifications?.notifications?.filter((n) => !n.delivered).length || 0;
  const recentNotifications = notifications?.notifications || [];

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case "task_completed":
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case "task_failed":
      case "system_error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case "crypto_signal":
        return <TrendingUp className="w-4 h-4 text-amber-500" />;
      case "job_match":
        return <Briefcase className="w-4 h-4 text-blue-500" />;
      case "agent_alert":
        return <Bot className="w-4 h-4 text-purple-500" />;
      default:
        return <Bell className="w-4 h-4 text-zinc-400" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "urgent":
        return "bg-red-500";
      case "high":
        return "bg-amber-500";
      case "normal":
        return "bg-blue-500";
      default:
        return "bg-zinc-500";
    }
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "Just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <header className="h-16 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between px-6">
      {/* Search */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search..."
            className="w-64 h-9 pl-10 pr-4 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* System Status */}
        <div className="flex items-center gap-2 text-sm">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-zinc-400">System Online</span>
        </div>

        {/* Telegram Status */}
        {telegramStatus?.enabled && (
          <div className="flex items-center gap-1">
            <MessageCircle
              className={`w-4 h-4 ${
                telegramStatus.connected ? "text-emerald-500" : "text-zinc-500"
              }`}
            />
            {telegramStatus.connected && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            )}
          </div>
        )}

        {/* Notifications */}
        <DropdownMenu open={showNotifications} onOpenChange={setShowNotifications}>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="relative text-zinc-400 hover:text-white"
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-80 bg-zinc-900 border-zinc-800 max-h-[500px] overflow-hidden"
          >
            <DropdownMenuLabel className="flex items-center justify-between text-zinc-300">
              <span>Notifications</span>
              <div className="flex items-center gap-2">
                {telegramStatus?.enabled && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.preventDefault();
                      testTelegramMutation.mutate();
                    }}
                    disabled={testTelegramMutation.isPending}
                    className="h-6 px-2 text-xs text-zinc-400 hover:text-white"
                  >
                    {testTelegramMutation.isPending ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <>
                        <Send className="w-3 h-3 mr-1" />
                        Test
                      </>
                    )}
                  </Button>
                )}
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-zinc-800" />

            <div className="max-h-[350px] overflow-y-auto">
              {notificationsLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-zinc-500" />
                </div>
              ) : recentNotifications.length > 0 ? (
                recentNotifications.map((notification) => (
                  <NotificationItem
                    key={notification.notification_id}
                    notification={notification}
                    getIcon={getNotificationIcon}
                    getPriorityColor={getPriorityColor}
                    formatTime={formatTime}
                  />
                ))
              ) : (
                <div className="text-center py-8 text-zinc-500">
                  <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No notifications</p>
                </div>
              )}
            </div>

            <DropdownMenuSeparator className="bg-zinc-800" />
            <div className="p-2">
              <Link href="/settings">
                <Button
                  variant="ghost"
                  size="sm"
                  className="w-full text-zinc-400 hover:text-white hover:bg-zinc-800"
                >
                  <Settings className="w-4 h-4 mr-2" />
                  Notification Settings
                </Button>
              </Link>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2 text-zinc-400 hover:text-white">
              <Avatar className="w-8 h-8">
                <AvatarFallback className="bg-zinc-800 text-white">
                  {user?.name?.charAt(0).toUpperCase() || "U"}
                </AvatarFallback>
              </Avatar>
              <span className="hidden md:inline">{user?.name || "User"}</span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48 bg-zinc-900 border-zinc-800">
            <DropdownMenuLabel className="text-zinc-400">My Account</DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-zinc-800" />
            <Link href="/settings">
              <DropdownMenuItem className="text-zinc-300 focus:bg-zinc-800 focus:text-white cursor-pointer">
                <User className="w-4 h-4 mr-2" />
                Profile
              </DropdownMenuItem>
            </Link>
            <Link href="/settings">
              <DropdownMenuItem className="text-zinc-300 focus:bg-zinc-800 focus:text-white cursor-pointer">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </DropdownMenuItem>
            </Link>
            <DropdownMenuSeparator className="bg-zinc-800" />
            <DropdownMenuItem
              onClick={logout}
              className="text-red-400 focus:bg-zinc-800 focus:text-red-400 cursor-pointer"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

function NotificationItem({
  notification,
  getIcon,
  getPriorityColor,
  formatTime,
}: {
  notification: Notification;
  getIcon: (type: string) => ReactNode;
  getPriorityColor: (priority: string) => string;
  formatTime: (date: string) => string;
}) {
  return (
    <div
      className={`px-3 py-2 hover:bg-zinc-800/50 transition-colors ${
        !notification.delivered ? "bg-zinc-800/30" : ""
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5">{getIcon(notification.type)}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium text-sm text-white truncate">
              {notification.title}
            </p>
            <span
              className={`w-1.5 h-1.5 rounded-full ${getPriorityColor(
                notification.priority
              )}`}
            />
          </div>
          <p className="text-xs text-zinc-400 line-clamp-2 mt-0.5">
            {notification.message}
          </p>
          <p className="text-xs text-zinc-500 mt-1">
            {formatTime(notification.created_at)}
          </p>
        </div>
        {!notification.delivered && (
          <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1" />
        )}
      </div>
    </div>
  );
}
