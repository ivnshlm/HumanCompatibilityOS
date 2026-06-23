import type { Metadata } from "next";
import { Inter_Tight } from "next/font/google";
import "./globals.css";

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
        <header className="border-b border-white/10">
          <div className="mx-auto flex max-w-6xl items-center px-6 py-3">
            <a href="/" className="flex items-center gap-2.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/hcos_logo.svg" alt="Human Compatibility OS" width={28} height={28} />
              <span className="text-sm font-semibold tracking-tight">
                Human Compatibility OS
              </span>
              <span className="hidden text-xs opacity-40 sm:inline">· Fabrika Sredy</span>
            </a>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
