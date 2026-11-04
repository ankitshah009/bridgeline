import type { Metadata, Viewport } from "next";
import { DM_Sans, Fraunces } from "next/font/google";
import { TopNav } from "@/components/ui/TopNav";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["opsz"],
  display: "swap",
});

const dmSans = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Bridgeline",
  description:
    "From home to a tech career: free training first, a last-dollar grant for the rest, and $0 for San Francisco residents.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#fbf6ec",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${fraunces.variable} ${dmSans.variable}`}>
      <body>
        <TopNav />
        <main>{children}</main>
        <footer className="foot">
          Bridgeline · built on Mistral + Elastic for Make SF Better · planning guidance, not legal advice
        </footer>
      </body>
    </html>
  );
}
