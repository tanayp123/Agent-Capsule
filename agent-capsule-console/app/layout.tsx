import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Capsule Console",
  description: "Local private trace review console for Agent Capsule"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
