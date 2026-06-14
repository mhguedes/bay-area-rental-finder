# Bay Area Rental Finder — hosted, auto-updating

A web page listing 1BR/1BA rentals ≤ $3,500 near **469 Sherwood Way, Menlo Park**,
ranked Menlo Park → Palo Alto → other spots near Stanford, then by distance.
Pulls from **Craigslist, Zillow, and SUpost**. You share one permanent link; the
recipient opens it anytime and hits **Refresh** for the latest. Updates daily.

## How it works (the important part)

Zillow and SUpost are JavaScript apps with bot protection — a plain cloud server
can't scrape them reliably. So the **scraping runs inside the Claude app** (which
can render those sites), and the result is **pushed to this GitHub repo**, which
GitHub Pages serves. Flow each day:

1. The Claude scheduled task fetches Craigslist + Zillow + SUpost, keeps the
   qualifying 1BR/1BA listings, and writes `raw_listings.json`.
2. It runs `build_site.py`, which ranks everything and regenerates `index.html`
   + `listings.json`.
3. It `git push`es the repo. The Pages workflow republishes the site.

Because scraping runs in the app, updates happen when the app is open around the
scheduled time (it catches up on next launch if it was closed).

## One-time setup (we'll do this together)

1. **GitHub account** — sign in / create one at https://github.com.
2. **New repo** — e.g. `bay-area-rental-finder`, **Public**, create it.
3. **Personal access token** — GitHub → Settings → Developer settings →
   Fine-grained tokens → generate one scoped to just this repo with
   **Contents: Read and write**. (This lets the daily task push updates.)
4. **Connect the local folder** — from this `bayarea-rental-finder/` folder we'll
   run `git init`, set the remote to the tokenized URL, and push. The token lives
   only in your local `.git/config` (never uploaded — `.git` isn't part of Pages).
5. **Turn on Pages** — repo **Settings → Pages → Source = GitHub Actions**.
6. **First publish** — the push triggers the "Publish rental finder to Pages"
   workflow; when it's green, the site is live at
   `https://<your-username>.github.io/bay-area-rental-finder/`. Share that link.

## Daily updates & refresh

- The scheduled task re-scrapes and pushes every day (~7:00 AM Pacific).
- The recipient's **Refresh** button reloads the latest published listings — they
  never need a new file from you.
- Force an update anytime: ask Claude to "run the housing refresh now," or in
  GitHub use **Actions → Run workflow**.

## Good to know

- **SUpost contact** requires a Stanford (@stanford.edu) login — fine for this
  recipient. Those rows are labeled with a purple "SUpost" badge.
- **Zillow** gives exact street addresses, so its rows rank most precisely; the
  address is shown right in the listing title.
- **Public link:** a public repo means anyone with the URL can view the page.
  Private + Pages requires a paid GitHub plan.
- **If a source is blocked** on a given day, the task keeps the previous data
  rather than wiping the page, and the on-page source buttons still let the
  recipient search each site directly.
- **Terms:** Zillow's terms discourage scraping; this is light, personal-use
  fetching and may occasionally break — the page degrades gracefully if so.
- **Edit criteria:** price/cities/target address live near the top of
  `build_site.py`.

## Files

| File | Purpose |
|------|---------|
| `build_site.py` | Ranks `raw_listings.json` and builds the page (stdlib only) |
| `raw_listings.json` | Latest scraped listings (refreshed daily by the app) |
| `index.html`, `listings.json` | Generated site served by Pages |
| `.github/workflows/deploy.yml` | Publishes the committed files to Pages on push |
| `scrape_and_build.py` | Deprecated shim → runs `build_site.py` |
