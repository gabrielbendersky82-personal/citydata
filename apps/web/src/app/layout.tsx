import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "citydata — neighborhood fit, explained",
  description:
    "Rank a city's neighborhoods by what YOU care about — safety, rent, schools, walkability, transit, hazards — with transparent, explainable scores from public data.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
