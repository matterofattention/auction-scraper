#!/usr/bin/env python3
"""Scrape the full Medusa auction house online catalogue into a single CSV.

Source: https://medusa.cloudcatalogus.nl (see scrape_cloudcatalogus.py for
the shared scraping logic used by all auction houses on this platform).
"""

from scrape_cloudcatalogus import scrape_all

BASE_URL = "https://medusa.cloudcatalogus.nl"
OUTPUT_CSV = "data/medusa_catalog.csv"

if __name__ == "__main__":
    scrape_all(BASE_URL, OUTPUT_CSV)
