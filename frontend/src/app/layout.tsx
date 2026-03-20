import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import { Sidebar } from "@/components/layout/sidebar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
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
          <div className="flex h-screen overflow-hidden bg-background">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
              <div className="container mx-auto p-6 max-w-7xl">
                {children}
              </div>
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
