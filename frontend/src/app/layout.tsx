import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Smart Market Watchlist",
  description:
    "State-aware attention engine for watchlists — what meaningfully changed since you last checked.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    // suppressHydrationWarning: browser extensions (e.g. Grammarly) inject attributes on <html>/<body>
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
