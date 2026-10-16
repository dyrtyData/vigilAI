import { ptBR } from "./locales/pt-br";

export const locales = ["en", "pt-br"] as const;
export type Locale = typeof locales[number];
export function localePath(locale: Locale) { return locale === "pt-br" ? "/" : "/en"; }
export function isLocale(value: string): value is Locale { return locales.some(locale => locale === value); }

/** English is the source language. Numbers, source quotations and identifiers stay unchanged. */
export function getTranslator(locale: Locale) {
  return (text: string) => locale === "pt-br" ? ptBR[text] ?? text : text;
}
