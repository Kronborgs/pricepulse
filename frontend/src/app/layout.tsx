import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import { AppShell } from "@/components/layout/app-shell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "PricePulse",
  description: "Self-hosted prisovervågning til danske webshops",
  icons: {
    icon: [
      { url: "/icon.png", type: "image/png" },
    ],
    apple: "/icon.png",
  },
  openGraph: {
    title: "PricePulse",
    description: "Self-hosted prisovervågning til danske webshops",
    images: [{ url: "/logo.png" }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="da" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <div className="flex flex-col h-screen overflow-hidden bg-background">
            {/* Brand gradient accent bar */}
            <div className="h-0.5 flex-shrink-0 bg-gradient-to-r from-[#29ABE2] via-[#8DC63F] to-[#F7941D]" />
            <AppShell>{children}</AppShell>
          </div>
        </Providers>
      </body>
    </html>
  );
}
