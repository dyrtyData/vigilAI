"use client";

import type { MouseEvent } from "react";
import { getTranslator, localePath, type Locale } from "@/lib/i18n";

/** Real links work without JavaScript; normal clicks also preserve the current section. */
export function LanguageSwitch({ locale }: { locale: Locale }) {
  const t = getTranslator(locale);
  function navigate(event: MouseEvent<HTMLAnchorElement>, next: Locale) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    window.location.assign(`${localePath(next)}${window.location.search}${window.location.hash}`);
  }
  return <div className="language-switch" role="group" aria-label={t("Site language")}>
    <a href={localePath("en")} hrefLang="en" lang="en" aria-label="English" aria-current={locale === "en" ? "page" : undefined} onClick={event => navigate(event, "en")}>EN</a>
    <a href={localePath("pt-br")} hrefLang="pt-BR" lang="pt-BR" aria-label="Português do Brasil" aria-current={locale === "pt-br" ? "page" : undefined} onClick={event => navigate(event, "pt-br")}>PT-BR</a>
  </div>;
}
