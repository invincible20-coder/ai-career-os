import type { Metadata } from "next";
import "./globals.css";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { cn } from "@/lib/utils";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "HuntAI — Autonomous Career Operating System",
  description:
    "AI-powered adaptive career operating system. Intelligent job discovery, autonomous applications, behavioral learning, and career strategy — all orchestrated by AI agents.",
  keywords: [
    "job hunting",
    "AI",
    "career",
    "autonomous",
    "resume",
    "cover letter",
    "career intelligence",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={cn("dark", GeistSans.variable, GeistMono.variable)} suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
