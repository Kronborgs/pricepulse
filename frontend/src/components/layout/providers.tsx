"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useServerEvents } from "@/hooks/useServerEvents";
import { useInactivityLogout } from "@/hooks/useInactivityLogout";
import { api } from "@/lib/api";
import { I18nProvider, LangAttrSync, LocaleSync } from "@/lib/i18n";

/** Mounts the SSE listener once inside the QueryClientProvider scope */
function SSEMount() {
  useServerEvents();
  return null;
}

/** Reads the current user's session_timeout_minutes and starts inactivity timer.
 *  Also syncs the user's stored locale preference into the i18n context. */
function InactivityMount() {
  const { data: user } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.auth.me(),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
  useInactivityLogout(user?.session_timeout_minutes);
  return <LocaleSync userLocale={user?.locale} />;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000,
            refetchOnWindowFocus: false,
            retry: 1,
          },
        },
      })
  );

  return (
    <I18nProvider>
      <LangAttrSync />
      <NuqsAdapter>
        <QueryClientProvider client={queryClient}>
          <SSEMount />
          <InactivityMount />
          {children}
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </NuqsAdapter>
    </I18nProvider>
  );
}
