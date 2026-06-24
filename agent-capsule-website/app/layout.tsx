import type { Metadata } from "next";

import "./globals.css";

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
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
