"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

const ACTIVITY_EVENTS = ["mousedown", "keydown", "scroll", "touchstart", "pointermove"];

/**
 * Kalder automatisk logout efter `timeoutMinutes` minutters inaktivitet.
 * Monteres kun hvis timeoutMinutes > 0.
 */
export function useInactivityLogout(timeoutMinutes: number | null | undefined) {
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!timeoutMinutes || timeoutMinutes <= 0) return;

    const ms = timeoutMinutes * 60 * 1000;
    let timer: ReturnType<typeof setTimeout>;

    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        try {
          await api.auth.logout();
        } catch {
          // Ignorer fejl — log stadig ud lokalt
        }
        queryClient.clear();
        router.push("/login");
      }, ms);
    };

    ACTIVITY_EVENTS.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset(); // Start timeren med det samme

    return () => {
      clearTimeout(timer);
      ACTIVITY_EVENTS.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [timeoutMinutes, router, queryClient]);
}
