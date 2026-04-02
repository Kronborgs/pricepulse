import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow } from "date-fns";
import { da, enGB } from "date-fns/locale";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

function dateFnsLocale(locale?: string) {
  return locale === "da" ? da : enGB;
}

export function formatPrice(
  price: number | null | undefined,
  currency = "DKK",
  locale?: string
): string {
  if (price == null) return "—";
  const lc = locale === "da" ? "da-DK" : "en-GB";
  return new Intl.NumberFormat(lc, {
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
  return format(new Date(dateStr), pattern, { locale: dateFnsLocale(locale) });
}

export function formatRelative(dateStr: string | null | undefined, locale?: string, neverLabel = "never"): string {
  if (!dateStr) return neverLabel;
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: dateFnsLocale(locale) });
}

export function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}
