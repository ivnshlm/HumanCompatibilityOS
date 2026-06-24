import type { Metadata } from "next";
import { Inter_Tight } from "next/font/google";
import "./globals.css";

import { AppShell } from "@/components/AppShell";

// Design-system typography: Inter Tight with Cyrillic, self-hosted via next/font
// (no layout shift). Exposed as a CSS variable consumed in globals.css.
const interTight = Inter_Tight({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter-tight",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Human Compatibility OS",
  description: "Мониторинг выгорания и устойчивости среды · Fabrika Sredy",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className={interTight.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
