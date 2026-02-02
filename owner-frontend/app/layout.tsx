import type { Metadata } from "next";
import "../styles/globals.css";

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
    <html lang="en">
      <body className="min-h-screen bg-white text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
