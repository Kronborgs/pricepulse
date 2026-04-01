import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ExchangeRates } from "@/types";

export function useExchangeRates() {
  return useQuery<ExchangeRates>({
    queryKey: ["exchange-rates"],
    queryFn: () => api.exchangeRates.get(),
    staleTime: 1000 * 60 * 30, // 30 min — ECB opdaterer én gang dagligt
    refetchOnWindowFocus: false,
  });
}
