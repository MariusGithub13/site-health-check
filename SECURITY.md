# Security notes

Site Health Check fetches addresses that a visitor types in. That makes it a target for abuse, so the defaults are strict.

## SSRF (server-side request forgery)
- Only `http` and `https`, only ports 80 and 443, no credentials in the URL.
- The host name is resolved and **every** address it resolves to must be public. Refused: private (RFC 1918), loopback, link-local (including the cloud metadata address 169.254.169.254), CGNAT (100.64.0.0/10), multicast, reserved and IPv6 unique-local ranges, and IPv4-mapped IPv6 forms of all of these.
- The check runs again on **every redirect hop**, and the headless browser re-checks **every request it makes** (sub-resources included).
- **DNS rebinding, plain fetches (closed):** the name is resolved once, validated, and the connection is made to that exact validated IP. The HTTP client never resolves the name itself; the URL, the `Host` header and the TLS server name (SNI and certificate check) stay the original host name. The real peer address is checked again after connect, and a fresh connection is used for every redirect hop. Covered by tests with a hostile resolver that flips its answer.
- Known limit: the headless browser (Chromium) does its own DNS lookup. We re-check every request it makes, but a rebinding answer between that check and its lookup is still theoretically possible for browser sub-requests. If you run this on a network with sensitive internal services, add an egress firewall rule that blocks private ranges for the container. This is the real defence in depth, and we recommend it.

## Abuse limits
- Per-client rate limit (default 6 scans per hour, `SHC_RATE_LIMIT`), kept in memory.
- Maximum 25 pages per scan (default 10), same host only.
- One scan at a time on the whole server; a second request gets a "busy" answer.
- `robots.txt` is respected. If it cannot be read, the site is not scanned.
- Honest User-Agent: `SiteHealthCheck/1.0 (+https://github.com/devaland/site-health-check)`.
- Timeouts on every request and every page load; response bodies are capped at 2 MB.

## Data
No account, no tracking, no database, nothing written to disk. A finished report is kept in memory for 15 minutes so it can be downloaded as PDF, then deleted. Restarting the container removes it at once.

## Deployment advice
Put it behind HTTPS (a reverse proxy). Set `SHC_TRUST_PROXY=1` only when a proxy you control sets `X-Forwarded-For`, otherwise the rate limit sees only the proxy. Do not publish port 8000 directly.

## Reporting a vulnerability
Email office@devaland.com with the details. Please do not open a public issue for a security problem.
