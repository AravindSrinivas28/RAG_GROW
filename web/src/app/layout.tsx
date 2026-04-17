import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "M1 RAG — Facts-only mutual fund Q&A",
  description:
    "Facts-only mutual fund FAQ assistant. No investment advice.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
