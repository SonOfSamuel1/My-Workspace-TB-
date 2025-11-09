import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TRPCProvider } from "@/lib/trpc/client";
import { Toaster } from "@/components/ui/toaster";
import { NotificationsProvider } from "@/components/notifications-provider";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Mail Agent Manager",
  description: "Manage your autonomous email agents with ease",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <TRPCProvider>
          <NotificationsProvider>
            {children}
            <Toaster />
          </NotificationsProvider>
        </TRPCProvider>
      </body>
    </html>
  );
}
