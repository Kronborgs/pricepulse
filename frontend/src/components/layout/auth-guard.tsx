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
 *
 * Props:
 * - adminOnly: restrict to admin (and optionally superuser if superuserAllowed=true)
 * - superuserAllowed: when combined with adminOnly, also allows superuser role
 */
export function AuthGuard({
  children,
  adminOnly = false,
  superuserAllowed = false,
}: {
  children: React.ReactNode;
  adminOnly?: boolean;
  superuserAllowed?: boolean;
}) {
  const router = useRouter();

  const { data: setupStatus, isLoading: setupLoading } = useQuery({
    queryKey: ["auth", "setup-status"],
    queryFn: () => api.auth.setupStatus(),
    staleTime: 60 * 1000,
    retry: false,
  });

  const { data: user, isLoading: userLoading, isError: userError } = useCurrentUser();

  const isRoleAllowed = (role: string | undefined) => {
    if (!adminOnly) return true;
    if (role === "admin") return true;
    if (superuserAllowed && role === "superuser") return true;
    return false;
  };

  useEffect(() => {
    if (setupLoading || userLoading) return;

    if (setupStatus && setupStatus.setup_required) {
      router.replace("/setup");
      return;
    }

    if (!user || userError) {
      router.replace("/login");
      return;
    }

    if (!isRoleAllowed(user.role)) {
      router.replace("/");
    }
  }, [setupLoading, userLoading, setupStatus, user, userError, adminOnly, superuserAllowed, router]);

  if (setupLoading || userLoading) return null;
  if (setupStatus?.setup_required) return null;
  if (!user || userError) return null;
  if (!isRoleAllowed(user.role)) return null;

  return <>{children}</>;
}
