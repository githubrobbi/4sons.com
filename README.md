# 4sons.com

Landing page for **4 Sons**, the software studio of **Sky, LLC** (the Nio family business).

- **Host:** Cloudflare (front-door Worker + Pages per brother); was GitHub Pages
- **Custom domain:** `4sons.com` (see `CNAME`)
- **Email:** unchanged — `*@4sons.com` catch-all stays at IONOS (do **not** alter MX/SPF DNS records)

## Purpose

Replaces the broken IONOS → WordPress.com forwarding (502) with a real, controlled-domain
page that clearly identifies the site as operated by Sky, LLC — supporting the Apple
Developer Program *Organization* enrollment for Sky, LLC.

## Deploy

See "Front door" below. MX/SPF records are left untouched so company email keeps working.

## Front door
The front door: a Cloudflare Worker serves the landing page from `site/` and proxies every
section to its own Cloudflare Pages project, so each section is a repository owned by its
author.

| Path | Pages project | Repository |
|---|---|---|
| `/` | (this Worker's assets) | this repo, `site/` |
| `/david/` | `4sons-david` | githubrobbi/david (to transfer to David) |
| `/son2/` .. `/son4/` | `4sons-son2` .. | one repo per brother; rename in `worker/routes.js` |

## The switch: publish or unpublish a section

`SECTIONS_ENABLED` on the Worker (a comma-separated list of section names) decides what is
live. Change it in the Cloudflare dashboard: Workers & Pages, this Worker, Settings,
Variables and Secrets, edit `SECTIONS_ENABLED`, Deploy. It takes effect within seconds, no
code deploy. A section that is off answers "not published" at its path and is missing from
the landing page; its repository and Pages project stay as they are, and its author can keep
working and previewing at `https://<pages-project>.pages.dev`.

## Add or change a section

1. The author creates a plain static repo (copy any section repo as the starter) and a Pages
   project connected to it (Cloudflare dashboard: Workers & Pages, Create, Pages, connect to git).
2. Add one line to `worker/routes.js`: `"name": "<pages-project>"`.
3. `npm test` (the routing table is tested), then `npm run deploy`.

## Deploy

```sh
npm install
npm test
npx wrangler deploy          # workers.dev until the zone is on Cloudflare, then the custom domain
```
