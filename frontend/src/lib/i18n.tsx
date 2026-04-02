"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import en, { type TranslationKey } from "@/lib/translations/en";
import da from "@/lib/translations/da";

// ── Types ─────────────────────────────────────────────────────────────────────

export type Locale = "en" | "da";

type Translations = typeof en;

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
}

// ── Translations map ──────────────────────────────────────────────────────────

const TRANSLATIONS: Record<Locale, Translations> = { en, da };

// ── Context ───────────────────────────────────────────────────────────────────

const I18nContext = createContext<I18nContextValue | null>(null);

// ── Provider ──────────────────────────────────────────────────────────────────

function getInitialLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem("pricepulse_locale");
  if (stored === "en" || stored === "da") return stored;
  return "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(getInitialLocale);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("pricepulse_locale", next);
    }
  }, []);

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>): string => {
      const dict = TRANSLATIONS[locale];
      let str: string = (dict as Record<string, string>)[key] ?? (en as Record<string, string>)[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          str = str.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
        }
      }
      return str;
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}

// ── LocaleSync: syncs user.locale from DB → context ──────────────────────────
// Import is deferred to avoid circular deps — call dynamically inside component.

export function LocaleSync({ userLocale }: { userLocale: string | null | undefined }) {
  const { locale, setLocale } = useI18n();

  useEffect(() => {
    if (userLocale === "en" || userLocale === "da") {
      if (userLocale !== locale) {
        setLocale(userLocale);
      }
    }
  // Only run when userLocale first becomes available
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userLocale]);

  return null;
}

// ── LangAttrSync: keeps <html lang="…"> in sync ───────────────────────────────

export function LangAttrSync() {
  const { locale } = useI18n();
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  return null;
}
