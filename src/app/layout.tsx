import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Golf Data Analysis - AI Coach",
  description: "Professional golf data analysis platform with AI-powered insights",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.Node;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
