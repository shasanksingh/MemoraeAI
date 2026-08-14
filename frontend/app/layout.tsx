import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/app-shell";

export const metadata: Metadata = {
  title: "Memorae - Personal Intelligence OS",
  description: "Evidence-first memory, knowledge graph, meetings, and personal workflows.",
  icons: {
    icon: "/favicon.svg",
  },
  openGraph: {
    title: "Memorae - Personal Intelligence OS",
    description: "Evidence-first memory, knowledge graph, meetings, and personal workflows.",
    images: ["/brand/memorae-intelligence-map.png"],
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
