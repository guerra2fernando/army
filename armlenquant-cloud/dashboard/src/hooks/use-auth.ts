"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { LoginCredentials, RegisterData } from "@/types/api";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, isAuthenticated, setUser, logout: storeLogout } = useAuthStore();

  // Get current user
  const { isLoading: isLoadingUser } = useQuery({
    queryKey: ["user"],
    queryFn: async () => {
      const user = await api.getMe();
      setUser(user);
      return user;
    },
    enabled: typeof window !== "undefined" && !!localStorage.getItem("token") && !user,
    retry: false,
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: (credentials: LoginCredentials) => api.login(credentials),
    onSuccess: (data) => {
      setUser(data.user);
      queryClient.invalidateQueries({ queryKey: ["user"] });
      router.push("/");
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: (data: RegisterData) => api.register(data),
    onSuccess: () => {
      router.push("/login?registered=true");
    },
  });

  // Logout
  const logout = () => {
    api.logout();
    storeLogout();
    queryClient.clear();
    router.push("/login");
  };

  return {
    user,
    isAuthenticated,
    isLoading: isLoadingUser,
    login: loginMutation.mutate,
    loginError: loginMutation.error,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutate,
    registerError: registerMutation.error,
    isRegistering: registerMutation.isPending,
    logout,
  };
}

