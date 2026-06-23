# 4sons.com

Landing page for **4 Sons**, the software studio of **Sky, LLC** (the Nio family business).

- **Host:** GitHub Pages (`githubrobbi`)
- **Custom domain:** `4sons.com` (see `CNAME`)
- **Email:** unchanged — `*@4sons.com` catch-all stays at IONOS (do **not** alter MX/SPF DNS records)

## Purpose

Replaces the broken IONOS → WordPress.com forwarding (502) with a real, controlled-domain
page that clearly identifies the site as operated by Sky, LLC — supporting the Apple
Developer Program *Organization* enrollment for Sky, LLC.

## Deploy

Static site. Push to `main`; GitHub Pages serves it. DNS apex/`www` records point at GitHub Pages.
MX/SPF records are left untouched so company email keeps working.
