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

export function formatDate(dateStr: string | null | undefined, locale?: string): string {
  if (!dateStr) return "\u2014";
  const pattern = locale === "da" ? "d. MMM yyyy HH:mm" : "d MMM yyyy HH:mm";
  return format(new Date(dateStr), pattern, { locale: _dateFnsLocale(locale) });
}

export function formatRelative(dateStr: string | null | undefined, locale?: string, neverLabel = "never"): string {
  if (!dateStr) return neverLabel;
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: _dateFnsLocale(locale) });
}

export function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}
