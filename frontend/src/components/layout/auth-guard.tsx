"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

/**
 * Wraps any page that requires authentication.
 *
 * Behaviour:
 * - If setup hasn't been done yet → redirect to /setup
 * - If the user is not logged in → redirect to /login
 * - While loading → render nothing (prevents flash)
 */
export function AuthGuard({ children, adminOnly = false }: { children: React.ReactNode; adminOnly?: boolean }) {
  const router = useRouter();

  const { data: setupStatus, isLoading: setupLoading } = useQuery({
    queryKey: ["auth", "setup-status"],
    queryFn: () => api.auth.setupStatus(),
    staleTime: 60 * 1000,
    retry: false,
  });

  const { data: user, isLoading: userLoading } = useCurrentUser();

  useEffect(() => {
    if (setupLoading || userLoading) return;

    if (setupStatus && setupStatus.setup_required) {
      router.replace("/setup");
      return;
    }

    if (!user) {
      router.replace("/login");
      return;
    }

    if (adminOnly && user.role !== "admin") {
      router.replace("/");
    }
  }, [setupLoading, userLoading, setupStatus, user, adminOnly, router]);

  if (setupLoading || userLoading) return null;
  if (setupStatus?.setup_required) return null;
  if (!user) return null;
  if (adminOnly && user.role !== "admin") return null;

  return <>{children}</>;
}
