import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Suspense } from "react";

import { AppHeader } from "@/components/layout/app-header";
import { QueryProvider } from "@/lib/query-provider";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Profile Scraper", template: "%s · Profile Scraper" },
  description: "Collect and browse LinkedIn profile data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <QueryProvider>
          <Suspense fallback={<div className="h-14 border-b border-border bg-surface" />}>
            <AppHeader />
          </Suspense>
          <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
            {children}
          </main>
        </QueryProvider>
      </body>
    </html>
  );
}
