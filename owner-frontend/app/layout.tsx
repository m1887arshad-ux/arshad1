import type { Metadata } from "next";
import "../styles/globals.css";
import { ThemeProvider } from "./theme-provider";

export const metadata: Metadata = {
  title: "Bharat Biz-Agent | Owner Control Panel",
  description: "Your business, your control.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-50 antialiased transition-colors duration-200">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
