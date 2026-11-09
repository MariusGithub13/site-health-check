"""English and Romanian text. Romanian uses diacritics and the formal 'dumneavoastră' form."""
LANGS = ("en", "ro")

UI = {
 "title": ("Site Health Check", "Verificare de sănătate a site-ului"),
 "lead": ("Enter a site address. You get one report on accessibility, display on phones, text contrast and broken links.",
          "Introduceți adresa site-ului dumneavoastră. Veți primi un singur raport despre accesibilitate, afișarea pe telefon, contrastul textului și linkurile defecte."),
 "url_label": ("Site address", "Adresa site-ului"),
 "pages_label": ("Pages to check (1 to %d, default %d)", "Pagini de verificat (de la 1 la %d, implicit %d)"),
 "run": ("Check this site", "Verificați acest site"),
 "wait": ("A scan of 10 pages takes about one to three minutes. Please keep this page open.",
          "O verificare de 10 pagini durează aproximativ un până la trei minute. Vă rugăm să păstrați această pagină deschisă."),
 "privacy": ("No account, no tracking. The report is kept in memory for 15 minutes so you can download it, then deleted. Only pages of the same site are opened, and robots.txt is respected.",
             "Fără cont și fără urmărirea vizitatorilor. Raportul este păstrat în memorie 15 minute, ca să îl puteți descărca, apoi este șters. Se deschid doar pagini ale aceluiași site, iar robots.txt este respectat."),
 "lang_switch": ("Română", "English"),
 "report_for": ("Report for", "Raport pentru"),
 "scanned": ("Pages examined", "Pagini examinate"),
 "of": ("of", "din"),
 "when": ("Date", "Data"),
 "download_pdf": ("Download as PDF", "Descărcați ca PDF"),
 "new_scan": ("Check another site", "Verificați alt site"),
 "honesty_title": ("What this report can and cannot tell you", "Ce vă poate și ce nu vă poate spune acest raport"),
 "honesty": ("Automated checks cover about a third of the WCAG 2.1 success criteria. A site that passes every check here can still be hard to use for people with disabilities; the rest needs a person to test it. Each check below is passed, failed, or could not be checked. \"Could not be checked\" never means \"no problems\".",
             "Verificările automate acoperă aproximativ o treime din criteriile de succes WCAG 2.1. Un site care trece toate verificările de aici poate fi totuși greu de folosit pentru persoanele cu dizabilități; restul trebuie testat de o persoană. Fiecare verificare de mai jos este reușită, eșuată sau nu a putut fi verificată. „Nu a putut fi verificată” nu înseamnă niciodată „nicio problemă”."),
 "passed": ("Passed", "Reușită"),
 "failed": ("Failed", "Eșuată"),
 "unknown": ("Could not check", "Nu a putut fi verificată"),
 "summary": ("Summary", "Rezumat"),
 "pages_list": ("Pages examined", "Paginile examinate"),
 "skipped": ("Skipped because robots.txt asks robots not to visit them", "Omise, deoarece robots.txt cere roboților să nu le viziteze"),
 "no_findings": ("Nothing to report on this page.", "Nimic de raportat pentru această pagină."),
 "links_examined": ("Links examined", "Linkuri examinate"),
 "links_broken": ("Broken links", "Linkuri defecte"),
 "links_unknown": ("Links that could not be checked", "Linkuri care nu au putut fi verificate"),
 "found_on": ("found on", "găsit pe"),
 "control": ("Control request to a path that cannot exist", "Cerere de control către o adresă care nu poate exista"),
 "control_ok": ("The site correctly answered %s, so its other answers can be trusted.", "Site-ul a răspuns corect %s, deci celelalte răspunsuri ale sale pot fi luate în considerare."),
 "control_bad": ("The site answers 200 to a page that cannot exist, so a 200 proves nothing here. Broken links could not be told apart.",
                 "Site-ul răspunde 200 la o pagină care nu poate exista, deci un 200 nu dovedește nimic aici. Linkurile defecte nu au putut fi identificate."),
 "control_err": ("The control request itself failed (%s), so the link check could not be trusted.", "Cererea de control a eșuat (%s), deci verificarea linkurilor nu a putut fi considerată de încredere."),
 "robots_skipped": ("%d link(s) not requested because robots.txt disallows them.", "%d linkuri nu au fost solicitate, deoarece robots.txt le interzice."),
 "capped": ("Only the first %d of %d distinct links were examined.", "Au fost examinate doar primele %d din %d linkuri distincte."),
 "fatal_refused": ("This address was refused: %s. Only public websites can be checked.", "Această adresă a fost refuzată: %s. Pot fi verificate doar site-uri publice."),
 "fatal_unreachable": ("The site could not be reached (%s). Nothing was measured, so no check is marked as passed.", "Site-ul nu a putut fi accesat (%s). Nu s-a măsurat nimic, deci nicio verificare nu este marcată ca trecută."),
 "fatal_home_status": ("The homepage answered with HTTP %s. Nothing was measured.", "Pagina principală a răspuns cu HTTP %s. Nu s-a măsurat nimic."),
 "fatal_robots_unreadable": ("robots.txt could not be read (%s), so we did not scan the site.", "Fișierul robots.txt nu a putut fi citit (%s), deci site-ul nu a fost verificat."),
 "fatal_robots_blocked": ("robots.txt asks robots not to visit this site, so we did not scan it.", "robots.txt cere roboților să nu viziteze acest site, deci nu l-am verificat."),
 "err_url": ("Please enter a valid web address, for example https://example.com", "Vă rugăm să introduceți o adresă web validă, de exemplu https://example.com"),
 "err_rate": ("Too many checks from your address. Please try again later.", "Prea multe verificări de la adresa dumneavoastră. Vă rugăm să încercați mai târziu."),
 "err_busy": ("A scan is already running on this server. Please try again in a few minutes.", "O verificare rulează deja pe acest server. Vă rugăm să încercați din nou peste câteva minute."),
 "err_gone": ("This report has expired and was deleted. Please run the check again.", "Acest raport a expirat și a fost șters. Vă rugăm să rulați din nou verificarea."),
 "footer_cta": ("Need a full audit or monthly monitoring?", "Aveți nevoie de un audit complet sau de monitorizare lunară?"),
 "footer_url": ("https://devaland.com", "https://devaland.cloud/servicii/accesibilitate-web.html"),
 "footer_note": ("Open source (MIT) by Devaland Marketing S.R.L.", "Cod deschis (MIT), de Devaland Marketing S.R.L."),
 "check_a11y": ("Accessibility", "Accesibilitate"),
 "check_overflow": ("Display on a phone (390 px wide)", "Afișare pe telefon (390 px lățime)"),
 "check_contrast": ("Text contrast", "Contrastul textului"),
 "check_links": ("Broken links", "Linkuri defecte"),
 "desc_a11y": ("Keyboard focus, image descriptions, link text, headings, language, touch targets, zoom.", "Focus la tastatură, descrierea imaginilor, textul linkurilor, titluri, limbă, ținte de atingere, mărire."),
 "desc_overflow": ("Does any element run off the edge of a phone screen?", "Iese vreun element din marginea ecranului unui telefon?"),
 "desc_contrast": ("Measured on the colours the browser really paints (WCAG AA: 4.5:1, large text 3:1).", "Măsurat pe culorile pe care browserul le desenează efectiv (WCAG AA: 4,5:1, text mare 3:1)."),
 "desc_links": ("Each internal link is requested once.", "Fiecare link intern este solicitat o singură dată."),
}

FINDINGS = {
 "open_failed": ("The page could not be opened (%(why)s).", "Pagina nu a putut fi deschisă (%(why)s)."),
 "http_status": ("The page answered HTTP %(status)s.", "Pagina a răspuns cu HTTP %(status)s."),
 "test_unavailable": ("The test \"%(test)s\" could not run on this page.", "Testul „%(test)s” nu a putut rula pe această pagină."),
 "focus_none": ("Keyboard: pressing Tab does not reach any element.", "Tastatură: tasta Tab nu ajunge la niciun element."),
 "focus_invisible": ("Keyboard: no visible focus indicator when pressing Tab.", "Tastatură: niciun indicator vizibil de focus la apăsarea tastei Tab."),
 "alt_missing": ("%(n)s of %(total)s images have no alt attribute.", "%(n)s din %(total)s imagini nu au atributul alt."),
 "link_text": ("Links with no meaning out of context: %(texts)s.", "Linkuri cu text neclar în afara contextului: %(texts)s."),
 "h1_count": ("The page has %(n)s h1 headings (it should have exactly 1).", "Pagina are %(n)s titluri h1 (ar trebui să aibă exact 1)."),
 "motion": ("%(n)s element(s) with an endless animation. Check that it can be stopped.", "%(n)s element(e) cu animație continuă. Verificați că poate fi oprită."),
 "no_statement": ("No link to an accessibility statement was found.", "Nu a fost găsit niciun link către o declarație de accesibilitate."),
 "no_lang": ("The html element has no lang attribute.", "Elementul html nu are atributul lang."),
 "no_title": ("The page has no title.", "Pagina nu are titlu."),
 "touch_target": ("Touch targets under 44x44 px in the header or menu: %(items)s.", "Ținte de atingere sub 44x44 px în antet sau meniu: %(items)s."),
 "zoom": ("Horizontal scrolling at 320 px (the same as 200% zoom on a 640 px screen).", "Derulare orizontală la 320 px (echivalent cu mărirea 200% pe un ecran de 640 px)."),
 "overflow": ("%(n)s element(s) run past the right edge of a 390 px screen: %(items)s", "%(n)s element(e) depășesc marginea dreaptă a unui ecran de 390 px: %(items)s"),
 "rendered_little": ("Only %(n)s characters of text were rendered, too little to judge.", "S-au afișat doar %(n)s caractere de text, prea puțin pentru o evaluare."),
 "contrast_low": ("Contrast %(ratio)s:1 (needs %(need)s:1), %(px)s px: \"%(text)s\"", "Contrast %(ratio)s:1 (necesar %(need)s:1), %(px)s px: „%(text)s”"),
 "no_text": ("No visible text was found to measure.", "Nu a fost găsit text vizibil care să poată fi măsurat."),
}


def ui(key, lang, *args):
    s = UI[key][1 if lang == "ro" else 0]
    return s % args if args else s


def finding(f, lang):
    s = FINDINGS[f["code"]][1 if lang == "ro" else 0]
    try:
        return s % f["params"]
    except (KeyError, TypeError):
        return s


def norm_lang(v):
    return v if v in LANGS else "en"
