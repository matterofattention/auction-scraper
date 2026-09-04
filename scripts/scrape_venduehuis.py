#!/usr/bin/env python3
"""Scrape the current Venduehuis auction house online catalogue into a CSV.

Source: https://auctions.venduehuis.com (see scrape_artisio.py for the
shared scraping logic used by all auction houses on the Artisio platform).
The client ID below is read from `window.artisioWebApp.clientId` in that
site's HTML.
"""

from scrape_artisio import scrape_all

SITE_ORIGIN = "https://auctions.venduehuis.com"
CLIENT_ID = "06162328"
OUTPUT_DIR = "data"
FILENAME_PREFIX = "venduehuis_catalog"

if __name__ == "__main__":
    scrape_all(SITE_ORIGIN, CLIENT_ID, OUTPUT_DIR, FILENAME_PREFIX)
