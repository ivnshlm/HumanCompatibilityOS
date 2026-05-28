import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Human Compatibility OS",
  description: "Мониторинг выгорания и устойчивости среды",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
