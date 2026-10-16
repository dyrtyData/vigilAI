import type { Metadata } from "next";
import "@fontsource-variable/manrope";
import "@fontsource/instrument-serif/latin-400.css";
import "@fontsource/instrument-serif/latin-400-italic.css";
import "../globals.css";
import { brand } from "@/lib/content";
import { getTranslator, isLocale, localePath, locales } from "@/lib/i18n";
import { notFound } from "next/navigation";

export function generateStaticParams() { return locales.map(locale => ({ locale })); }
export const dynamicParams = false;

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const t = getTranslator(locale);
  return {
  title: `${brand.name} — ${t("Rights-based evaluation of language models.")}`,
  description: t("A research summary of Vigil AI: adapting COMPL-AI to Brazil’s PL 2338/2023, auditing measurement validity, and reporting corrected results and limitations."),
  alternates: { languages: { en: localePath("en"), "pt-BR": localePath("pt-br"), "x-default": localePath("pt-br") } },
  icons: { icon: "/icon.svg" },
  // Keep the local research preview out of search indexes until publication.
  robots: { index: false, follow: false },
  };
}

export default async function RootLayout({ children, params }: Readonly<{ children: React.ReactNode; params: Promise<{ locale: string }> }>) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <html lang={locale === "pt-br" ? "pt-BR" : "en"}><body>{children}</body></html>;
}
