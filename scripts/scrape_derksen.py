#!/usr/bin/env python3
"""Scrape the full Derksen auction house online catalogue into a single CSV.

Source: https://derksen.cloudcatalogus.nl (see scrape_cloudcatalogus.py for
the shared scraping logic used by all auction houses on this platform).
"""

from scrape_cloudcatalogus import scrape_all

BASE_URL = "https://derksen.cloudcatalogus.nl"
OUTPUT_DIR = "data"
FILENAME_PREFIX = "derksen_catalog"

if __name__ == "__main__":
    scrape_all(BASE_URL, OUTPUT_DIR, FILENAME_PREFIX)
