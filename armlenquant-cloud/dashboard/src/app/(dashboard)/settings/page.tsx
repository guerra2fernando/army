"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/use-auth";
import type { UserSettings } from "@/types/api";
import {
  Settings,
  User,
  Bell,
  Palette,
  Shield,
  Key,
  Mail,
  MessageCircle,
  Save,
  Loader2,
  CheckCircle,
  LogOut,
  Moon,
  Sun,
  Monitor,
  TrendingUp,
  Briefcase,
  Send,
  XCircle,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [telegramTestResult, setTelegramTestResult] = useState<"success" | "error" | null>(null);

  const { data: settings, isLoading } = useQuery({
    queryKey: ["user-settings"],
    queryFn: () => api.getUserSettings(),
  });

  const { data: telegramStatus } = useQuery({
    queryKey: ["telegram-status"],
    queryFn: () => api.getTelegramStatus(),
    retry: false,
  });

  const [localSettings, setLocalSettings] = useState<Partial<UserSettings>>({});

  useEffect(() => {
    if (settings) {
      setLocalSettings(settings);
    }
  }, [settings]);

  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<UserSettings>) => api.updateUserSettings(newSettings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const testTelegramMutation = useMutation({
    mutationFn: () => api.testTelegramNotification(),
    onSuccess: () => {
      setTelegramTestResult("success");
      setTimeout(() => setTelegramTestResult(null), 3000);
    },
    onError: () => {
      setTelegramTestResult("error");
      setTimeout(() => setTelegramTestResult(null), 3000);
    },
  });

  const handleSave = () => {
    updateSettingsMutation.mutate(localSettings);
  };

  const updateSetting = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setLocalSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Settings</h1>
          <p className="text-zinc-400">Manage your account and preferences</p>
        </div>
        <Button
          onClick={handleSave}
          disabled={updateSettingsMutation.isPending}
          className="bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
        >
          {updateSettingsMutation.isPending ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : saved ? (
            <CheckCircle className="w-4 h-4 mr-2" />
          ) : (
            <Save className="w-4 h-4 mr-2" />
          )}
          {saved ? "Saved!" : "Save Changes"}
        </Button>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Profile Section */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <User className="w-5 h-5 text-emerald-500" />
                Profile
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Your account information
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center text-2xl font-bold text-black">
                  {user?.name?.charAt(0)?.toUpperCase() || "U"}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">{user?.name || "User"}</h3>
                  <p className="text-zinc-400">{user?.email}</p>
                  <Badge variant="outline" className="mt-1 border-emerald-500/20 text-emerald-500 bg-emerald-500/10">
                    {user?.is_admin ? "Administrator" : "User"}
                  </Badge>
                </div>
              </div>
              <Separator className="bg-zinc-800" />
              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label className="text-zinc-300">Email</Label>
                  <Input
                    value={user?.email || ""}
                    disabled
                    className="bg-zinc-800 border-zinc-700 text-zinc-400"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-zinc-300">Name</Label>
                  <Input
                    value={user?.name || ""}
                    disabled
                    className="bg-zinc-800 border-zinc-700 text-zinc-400"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Notifications Section */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Bell className="w-5 h-5 text-emerald-500" />
                Notifications
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Configure how you receive alerts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Bell className="w-5 h-5 text-zinc-400" />
                  <div>
                    <p className="font-medium text-white">Enable Notifications</p>
                    <p className="text-sm text-zinc-500">Receive alerts for important events</p>
                  </div>
                </div>
                <Switch
                  checked={localSettings.notifications_enabled ?? true}
                  onCheckedChange={(checked) => updateSetting("notifications_enabled", checked)}
                />
              </div>
              <Separator className="bg-zinc-800" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-zinc-400" />
                  <div>
                    <p className="font-medium text-white">Email Notifications</p>
                    <p className="text-sm text-zinc-500">Receive notifications via email</p>
                  </div>
                </div>
                <Switch
                  checked={localSettings.email_notifications ?? true}
                  onCheckedChange={(checked) => updateSetting("email_notifications", checked)}
                  disabled={!localSettings.notifications_enabled}
                />
              </div>
              <Separator className="bg-zinc-800" />
              
              {/* Telegram Section */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-zinc-400" />
                    <div>
                      <p className="font-medium text-white">Telegram Notifications</p>
                      <p className="text-sm text-zinc-500">Receive notifications via Telegram</p>
                    </div>
                  </div>
                  <Switch
                    checked={localSettings.telegram_notifications ?? false}
                    onCheckedChange={(checked) => updateSetting("telegram_notifications", checked)}
                    disabled={!localSettings.notifications_enabled}
                  />
                </div>

                {/* Telegram Status */}
                {telegramStatus && (
                  <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-800/50">
                    <div className="flex items-center gap-3">
                      {telegramStatus.enabled ? (
                        telegramStatus.connected ? (
                          <Wifi className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <WifiOff className="w-5 h-5 text-amber-500" />
                        )
                      ) : (
                        <WifiOff className="w-5 h-5 text-zinc-500" />
                      )}
                      <div>
                        <p className="text-sm font-medium text-white">
                          {telegramStatus.enabled
                            ? telegramStatus.connected
                              ? "Telegram Connected"
                              : "Telegram Enabled (not connected)"
                            : "Telegram Disabled"}
                        </p>
                        <p className="text-xs text-zinc-500">
                          {telegramStatus.chat_id_configured
                            ? "Chat ID configured"
                            : "Chat ID not configured"}
                        </p>
                      </div>
                    </div>
                    {telegramStatus.enabled && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => testTelegramMutation.mutate()}
                        disabled={testTelegramMutation.isPending}
                        className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                      >
                        {testTelegramMutation.isPending ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : telegramTestResult === "success" ? (
                          <>
                            <CheckCircle className="w-4 h-4 mr-1 text-emerald-500" />
                            Sent!
                          </>
                        ) : telegramTestResult === "error" ? (
                          <>
                            <XCircle className="w-4 h-4 mr-1 text-red-500" />
                            Failed
                          </>
                        ) : (
                          <>
                            <Send className="w-4 h-4 mr-1" />
                            Test
                          </>
                        )}
                      </Button>
                    )}
                  </div>
                )}

                {localSettings.telegram_notifications && (
                  <div className="space-y-2 pl-8">
                    <Label className="text-zinc-300">Telegram Chat ID</Label>
                    <Input
                      value={localSettings.telegram_chat_id || ""}
                      onChange={(e) => updateSetting("telegram_chat_id", e.target.value)}
                      placeholder="Enter your Telegram chat ID"
                      className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    />
                    <p className="text-xs text-zinc-500">
                      Get your chat ID by messaging @userinfobot on Telegram
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Appearance Section */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Palette className="w-5 h-5 text-emerald-500" />
                Appearance
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Customize the look of the dashboard
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label className="text-zinc-300">Theme</Label>
                <Select
                  value={localSettings.theme || "dark"}
                  onValueChange={(value) => updateSetting("theme", value as "dark" | "light" | "system")}
                >
                  <SelectTrigger className="w-full bg-zinc-800 border-zinc-700 text-zinc-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-800">
                    <SelectItem value="dark" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      <div className="flex items-center gap-2">
                        <Moon className="w-4 h-4" />
                        Dark
                      </div>
                    </SelectItem>
                    <SelectItem value="light" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      <div className="flex items-center gap-2">
                        <Sun className="w-4 h-4" />
                        Light
                      </div>
                    </SelectItem>
                    <SelectItem value="system" className="text-zinc-300 focus:bg-zinc-800 focus:text-white">
                      <div className="flex items-center gap-2">
                        <Monitor className="w-4 h-4" />
                        System
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Agent Defaults Section */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Settings className="w-5 h-5 text-emerald-500" />
                Agent Defaults
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Default settings for agent tasks
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-zinc-300">
                  <Briefcase className="w-4 h-4" />
                  <span className="font-medium">Job Hunter</span>
                </div>
                <div className="grid gap-4 pl-6">
                  <div className="space-y-2">
                    <Label className="text-zinc-400">Default Job Titles (comma-separated)</Label>
                    <Input
                      value={localSettings.default_job_titles?.join(", ") || ""}
                      onChange={(e) => updateSetting(
                        "default_job_titles",
                        e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                      )}
                      placeholder="Python Developer, Backend Engineer"
                      className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-zinc-400">Default Locations (comma-separated)</Label>
                    <Input
                      value={localSettings.default_job_locations?.join(", ") || ""}
                      onChange={(e) => updateSetting(
                        "default_job_locations",
                        e.target.value.split(",").map((s) => s.trim()).filter(Boolean)
                      )}
                      placeholder="Remote, Berlin, London"
                      className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                    />
                  </div>
                </div>
              </div>
              <Separator className="bg-zinc-800" />
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-zinc-300">
                  <TrendingUp className="w-4 h-4" />
                  <span className="font-medium">Crypto Sentinel</span>
                </div>
                <div className="space-y-2 pl-6">
                  <Label className="text-zinc-400">Watchlist (comma-separated)</Label>
                  <Input
                    value={localSettings.crypto_watchlist?.join(", ") || ""}
                    onChange={(e) => updateSetting(
                      "crypto_watchlist",
                      e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
                    )}
                    placeholder="BTC, ETH, SOL"
                    className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Security Section */}
          <Card className="bg-zinc-900/50 border-zinc-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <Shield className="w-5 h-5 text-emerald-500" />
                Security
              </CardTitle>
              <CardDescription className="text-zinc-400">
                Manage your security settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-4 rounded-lg bg-zinc-800/50">
                <div className="flex items-center gap-3">
                  <Key className="w-5 h-5 text-zinc-400" />
                  <div>
                    <p className="font-medium text-white">Change Password</p>
                    <p className="text-sm text-zinc-500">Update your account password</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
                >
                  Change
                </Button>
              </div>
              <div className="flex items-center justify-between p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <div className="flex items-center gap-3">
                  <LogOut className="w-5 h-5 text-red-500" />
                  <div>
                    <p className="font-medium text-white">Sign Out</p>
                    <p className="text-sm text-zinc-500">Log out of your account</p>
                  </div>
                </div>
                <Button
                  variant="destructive"
                  onClick={logout}
                  className="bg-red-500/10 text-red-500 hover:bg-red-500/20 border border-red-500/20"
                >
                  Sign Out
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

