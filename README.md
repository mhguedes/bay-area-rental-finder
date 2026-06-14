# Bay Area Rental Finder — hosted, auto-updating

Live site: **https://mhguedes.github.io/bay-area-rental-finder/**

A web page listing 1BR/1BA rentals ≤ $3,500 near **469 Sherwood Way, Menlo Park**,
ranked Menlo Park → Palo Alto → other spots near Stanford, then by distance.
Pulls from **Craigslist, Zillow, and SUpost**. Share the link once; the recipient
opens it anytime and hits **Refresh** for the latest. Updates daily.

## How it works

Zillow and SUpost are JavaScript apps with bot protection that a plain cloud
server can't scrape, so the **scraping runs inside the Claude app** (which renders
those sites) and the result is **pushed to this repo**. GitHub Pages serves the
committed files (deploy from the `main` branch, root). Each day the Claude
scheduled task:

1. Fetches Craigslist + Zillow + SUpost and keeps the qualifying 1BR/1BA listings.
2. Writes `raw_listings.json` and runs `build_site.py` to regenerate
   `index.html` + `listings.json`.
3. Clones the repo to a temp dir, copies the new files in, commits, and pushes.
   Pushing to `main` automatically republishes the Pages site.

Updates happen when the Claude app is open around the scheduled time (it catches
up on next launch if it was closed).

## Hosting setup (already done)

- Pages: **Settings → Pages → Source = Deploy from a branch → `main` / `(root)`**.
- Push auth: a fine-grained personal access token scoped to this repo
  (Contents: read/write). It lives only in `Housing/.gh_token` on the local
  machine — never committed here. Revoke/rotate anytime at GitHub → Settings →
  Developer settings → Fine-grained tokens.

## Good to know

- **SUpost contact** needs a Stanford (@stanford.edu) login (purple "SUpost" badge).
- **Zillow** rows include exact street addresses, so they rank most precisely.
- **Public link:** anyone with the URL can view the page. Private Pages needs a paid plan.
- **If a source is blocked** on a given day, the task keeps the previous data and
  the on-page source buttons still let you search each site directly.
- **Edit criteria:** price/cities/target address live near the top of `build_site.py`.

## Files

| File | Purpose |
|------|---------|
| `build_site.py` | Ranks `raw_listings.json` and builds the page (stdlib only) |
| `raw_listings.json` | Latest scraped listings (refreshed daily) |
| `index.html`, `listings.json` | Generated site served by Pages |
| `scrape_and_build.py` | Deprecated shim → runs `build_site.py` |
