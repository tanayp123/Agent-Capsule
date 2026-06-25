import type { Metadata } from "next";
import { Geist_Mono, Hanken_Grotesk } from "next/font/google";

import "./globals.css";

const hanken = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"]
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"]
});

export const metadata: Metadata = {
  title: "Agent Capsule",
  description: "Private agent debugging, policy review, safe traces, and confidential customer demos."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${hanken.variable} ${geistMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
