import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CoolShift — Intelligent Cooling Optimization",
  description: "AI-powered energy-efficient cooling for SDG 7 & SDG 13. Reduce cost, emissions and peak demand.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geist.variable} dark antialiased`}>
      <body className="min-h-screen bg-[#080d1a] text-slate-100">{children}</body>
    </html>
  );
}
