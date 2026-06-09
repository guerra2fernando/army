"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, Zap } from "lucide-react";
import { AxiosError } from "axios";

export default function LoginPage() {
  const { login, isLoggingIn, loginError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login({ email, password });
  };

  const getErrorMessage = (error: Error | null) => {
    if (!error) return null;
    if (error instanceof AxiosError) {
      return error.response?.data?.detail || "Invalid credentials";
    }
    return error.message || "Invalid credentials";
  };

  return (
    <Card className="w-full bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center mb-4">
          <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Zap className="w-7 h-7 text-black" />
          </div>
        </div>
        <CardTitle className="text-2xl text-center text-white">Welcome back</CardTitle>
        <CardDescription className="text-center text-zinc-400">
          Sign in to your ArmLenQuant account
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {loginError && (
            <Alert variant="destructive" className="bg-red-500/10 border-red-500/50 text-red-400">
              <AlertDescription>
                {getErrorMessage(loginError)}
              </AlertDescription>
            </Alert>
          )}
          <div className="space-y-2">
            <Label htmlFor="email" className="text-zinc-300">Email</Label>
            <Input
              id="email"
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-zinc-300">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4 mt-4">
          <Button
            type="submit"
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
            disabled={isLoggingIn}
          >
            {isLoggingIn && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Sign In
          </Button>
          <p className="text-sm text-zinc-400 text-center">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-emerald-500 hover:underline">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}

