import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow } from "date-fns";
import { da } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(
  price: number | null | undefined,
  currency = "DKK"
): string {
  if (price == null) return "—";
  return new Intl.NumberFormat("da-DK", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(price);
}

export function formatDelta(delta: number | null | undefined): string {
  if (delta == null) return "";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${formatPrice(delta)}`;
}

export function formatPct(pct: number | null | undefined): string {
  if (pct == null) return "";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return format(new Date(dateStr), "d. MMM yyyy HH:mm", { locale: da });
}

export function formatRelative(dateStr: string | null | undefined): string {
  if (!dateStr) return "aldrig";
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: da });
}

export function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}
