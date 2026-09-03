import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Timeless Compass — Dashboard",
  description: "Automated history documentary video pipeline",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen">
        {/* --- Sidebar navigation --- */}
        <Sidebar />

        {/* --- Main content area --- */}
        <main className="flex-1 ml-[240px] p-8">
          {children}
        </main>
      </body>
    </html>
  );
}
