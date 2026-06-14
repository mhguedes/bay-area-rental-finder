#!/usr/bin/env python3
"""DEPRECATED. Replaced by build_site.py.

Scraping now runs inside the Claude app (where Zillow & SUpost render), which
writes raw_listings.json and runs build_site.py. This cloud Playwright scraper
is no longer used; kept only to avoid a dangling import. Run build_site.py.
"""
import runpy, pathlib
runpy.run_path(str(pathlib.Path(__file__).resolve().parent / "build_site.py"), run_name="__main__")
