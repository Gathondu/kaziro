import type { Metadata } from "next";
import { Geist_Mono, Handlee, Plus_Jakarta_Sans } from "next/font/google";
import Script from "next/script";
import { QueryProvider } from "@/components/providers/QueryProvider";
import { ToastHost } from "@/components/ui/ToastHost";
import "./globals.css";

const plusJakarta = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const handlee = Handlee({
  variable: "--font-handlee",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "Kaziro",
  description: "AI-powered job recommendations and application documents.",
};

const themeScript = `
(function () {
  try {
    function themeForSystem() {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "terracotta_dark"
        : "terracotta";
    }
    var raw = null;
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i += 1) {
      var entry = cookies[i].trim();
      if (entry.indexOf("appearance=") === 0) {
        raw = decodeURIComponent(entry.slice("appearance=".length));
        break;
      }
    }
    var theme = raw === "dark" ? "terracotta_dark" : raw === "light" ? "terracotta" : themeForSystem();
    document.documentElement.setAttribute("data-theme", theme);
  } catch (_) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${plusJakarta.variable} ${geistMono.variable} ${handlee.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-base-100 text-base-content">
        <Script id="kaziro-theme" strategy="beforeInteractive">
          {themeScript}
        </Script>
        <QueryProvider>
          {children}
          <ToastHost />
        </QueryProvider>
      </body>
    </html>
  );
}
