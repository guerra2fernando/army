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

export default function RegisterPage() {
  const { register, isRegistering, registerError } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    register({ name, email, password });
  };

  const getErrorMessage = (error: Error | null) => {
    if (!error) return null;
    if (error instanceof AxiosError) {
      return error.response?.data?.detail || "Registration failed";
    }
    return error.message || "Registration failed";
  };

  return (
    <Card className="w-full bg-zinc-900/50 border-zinc-800 backdrop-blur-sm">
      <CardHeader className="space-y-1">
        <div className="flex items-center justify-center mb-4">
          <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center">
            <Zap className="w-7 h-7 text-black" />
          </div>
        </div>
        <CardTitle className="text-2xl text-center text-white">Create an account</CardTitle>
        <CardDescription className="text-center text-zinc-400">
          Get started with ArmLenQuant
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          {registerError && (
            <Alert variant="destructive" className="bg-red-500/10 border-red-500/50 text-red-400">
              <AlertDescription>
                {getErrorMessage(registerError)}
              </AlertDescription>
            </Alert>
          )}
          <div className="space-y-2">
            <Label htmlFor="name" className="text-zinc-300">Name</Label>
            <Input
              id="name"
              type="text"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>
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
              minLength={8}
              className="bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500 focus:ring-emerald-500 focus:border-emerald-500"
            />
            <p className="text-xs text-zinc-500">Minimum 8 characters</p>
          </div>
        </CardContent>
        <CardFooter className="flex flex-col space-y-4 mt-4">
          <Button
            type="submit"
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-black font-semibold"
            disabled={isRegistering}
          >
            {isRegistering && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            Create Account
          </Button>
          <p className="text-sm text-zinc-400 text-center">
            Already have an account?{" "}
            <Link href="/login" className="text-emerald-500 hover:underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}

