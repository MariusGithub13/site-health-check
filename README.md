# Site Health Check

A small, self-hosted web app. Enter a site address and get one report on:

- **Accessibility** (keyboard focus, image alt text, link text, headings, page language, touch targets, zoom)
- **Display on a phone** (does any element run off a 390 px screen)
- **Text contrast** (measured on the colours the browser really paints)
- **Broken links** (each internal link once, plus a control request to a path that cannot exist, so a site that answers 200 to everything is reported as such)

The report is HTML, can be downloaded as PDF, and is available in English and Romanian.

## Honest limits
Automated checks cover about a third of the WCAG 2.1 success criteria. Every report says so. Each check ends in one of three states: **passed**, **failed**, or **could not check**. A page that could not be fetched is never reported as "no problems".

## Quick start

```bash
git clone https://github.com/devaland/site-health-check
cd site-health-check
docker compose up --build
```

Open http://127.0.0.1:8000. Put an HTTPS reverse proxy in front before exposing it.

Without Docker (Python 3.10+):

```bash
pip install -r requirements.txt && playwright install --with-deps chromium
python -m shc          # binds 127.0.0.1:8000
```

Settings (environment variables): `SHC_HOST`, `SHC_PORT`, `SHC_RATE_LIMIT` (scans per client per hour, default 6), `SHC_TRUST_PROXY=1` (behind your own reverse proxy).

## Safety
SSRF guard (public addresses only, also after redirects), per-client rate limit, at most 25 pages per scan, same host only, robots.txt respected, honest User-Agent, timeouts everywhere, nothing stored after the report. Details in [SECURITY.md](SECURITY.md).

## Tests

```bash
pip install -r requirements-dev.txt && pytest
python scripts/smoke.py https://example.com 3     # starts the app locally, scans, downloads the PDF
```

## Deploy to Hostinger
TODO: the one-click deploy button is not set up yet.

## Need more?
A full audit or monthly monitoring: https://devaland.com (Romanian public sector: https://devaland.cloud/servicii/accesibilitate-web.html)

## In română
Site Health Check este o aplicație web mică, pe care o instalați pe propriul server. Introduceți adresa unui site și primiți un singur raport despre accesibilitate, afișarea pe telefon, contrastul textului și linkurile defecte, în română și engleză, cu descărcare PDF.

Rețineți: verificările automate acoperă aproximativ o treime din criteriile WCAG 2.1. Fiecare verificare are trei rezultate: trecută, picată sau nu a putut fi verificată. Nu se păstrează date după raport, nu există cont și nu există urmărire.

Instalare: `docker compose up --build`, apoi deschideți http://127.0.0.1:8000. Pentru un audit complet sau monitorizare lunară: https://devaland.cloud/servicii/accesibilitate-web.html

## Licence
MIT, Copyright (c) 2026 Devaland Marketing S.R.L.
