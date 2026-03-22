import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

export type SSEEvent = {
  type: string;
  data?: unknown;
};

/**
 * Opens a persistent SSE connection to /api/v1/events and invalidates
 * the appropriate React Query keys when events arrive.
 */
const EVENT_QUERY_MAP: Record<string, string[][]> = {
  price_updated: [["watches"], ["products"]],
  source_checked: [["watches"], ["sources"]],
  watch_created: [["watches"]],
  watch_updated: [["watches"]],
  watch_deleted: [["watches"]],
  ai_job_updated: [["ai", "jobs"]],
  email_sent: [["me", "email-preferences"]],
};

export function useServerEvents() {
  const queryClient = useQueryClient();
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL ?? "";
    const url = `${base}/api/v1/events`;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let retries = 0;

    function connect() {
      const es = new EventSource(url, { withCredentials: true });
      esRef.current = es;

      es.onmessage = (event) => {
        try {
          const payload: SSEEvent = JSON.parse(event.data);
          const keys = EVENT_QUERY_MAP[payload.type];
          if (keys) {
            keys.forEach((key) =>
              queryClient.invalidateQueries({ queryKey: key })
            );
          }
        } catch {
          // ignore parse errors
        }
      };

      es.onerror = () => {
        es.close();
        esRef.current = null;
        // Exponential back-off capped at 30 s
        const delay = Math.min(1000 * 2 ** retries, 30_000);
        retries += 1;
        retryTimeout = setTimeout(connect, delay);
      };

      es.onopen = () => {
        retries = 0;
      };
    }

    connect();

    return () => {
      if (retryTimeout) clearTimeout(retryTimeout);
      esRef.current?.close();
    };
  }, [queryClient]);
}
