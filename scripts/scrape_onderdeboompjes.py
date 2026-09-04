#!/usr/bin/env python3
"""Scrape the current Onder de Boompjes auction house online catalogue into a CSV.

Source: https://new.onderdeboompjes.nl/public/. The site is a Vue SPA whose
lot data comes from a plain JSON API:
  GET  /api/public/auction/default          -> the currently featured auction
  POST /api/public/lots {aid, page, qty}    -> a page of lots for that auction
Each lots response reports the total "quantity" alongside the page of
"items", so pages are fetched until all items are collected. Lot images are
served at /media/{uuid} (no /api prefix, discovered from the app bundle).
"""

import csv
import time
from collections import Counter

import requests

BASE_URL = "https://new.onderdeboompjes.nl"
OUTPUT_DIR = "data"
FILENAME_PREFIX = "onderdeboompjes_catalog"
PAGE_SIZE = 500
REQUEST_DELAY_SECONDS = 0.5

FIELDNAMES = [
    "LotNumber", "LotID", "LotStatus", "ItemStatus", "AuctionID", "AuctionTitle",
    "AuctionCategory", "Tags", "Title", "Description", "DisplayArtist",
    "ArtistAttribution", "ArtistTimePeriod", "HasArtistResaleRight", "School",
    "TimePeriod", "Quality", "Measurements", "TargetPriceLow", "TargetPriceHigh",
    "CatalogPrice", "HammerPrice", "HighestBid", "LiveAuction", "AuctionEndTime",
    "MediaCount", "ImageURLs",
]

session = requests.Session()


def get_default_auction():
    response = session.get(f"{BASE_URL}/api/public/auction/default", timeout=30)
    response.raise_for_status()
    return response.json()


def get_lots_page(auction_id, page, qty):
    response = session.post(
        f"{BASE_URL}/api/public/lots",
        json={"aid": auction_id, "page": page, "qty": qty},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_all_lots(auction_id):
    lots = []
    total = None
    page = 1

    while total is None or len(lots) < total:
        payload = get_lots_page(auction_id, page, PAGE_SIZE)
        total = payload["quantity"]
        batch = payload["items"]
        if not batch:
            break

        lots.extend(batch)
        print(f"  page {page}: +{len(batch)} lots ({len(lots)}/{total})")

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return lots


def image_url(uuid):
    return f"{BASE_URL}/media/{uuid}"


def flatten_lot(lot):
    item = lot.get("item") or {}
    artist = item.get("artist") or {}
    media = sorted(item.get("media") or [], key=lambda m: m.get("ordinal_number") or 0)

    return {
        "LotNumber": lot.get("lot_number"),
        "LotID": lot.get("id"),
        "LotStatus": lot.get("lot_status"),
        "ItemStatus": lot.get("item_status"),
        "AuctionID": lot.get("auction_id"),
        "AuctionTitle": lot.get("auction_title"),
        "AuctionCategory": lot.get("auction_category"),
        "Tags": ";".join(item.get("tags") or []),
        "Title": item.get("title"),
        "Description": item.get("description"),
        "DisplayArtist": item.get("display_artist"),
        "ArtistAttribution": item.get("artist_attribution"),
        "ArtistTimePeriod": artist.get("time_period"),
        "HasArtistResaleRight": item.get("has_artist_resale_right"),
        "School": item.get("school"),
        "TimePeriod": item.get("time_period"),
        "Quality": item.get("quality"),
        "Measurements": item.get("measurements"),
        "TargetPriceLow": lot.get("target_price_1"),
        "TargetPriceHigh": lot.get("target_price_2"),
        "CatalogPrice": lot.get("catalog_price"),
        "HammerPrice": lot.get("hammer_price"),
        "HighestBid": lot.get("highest_bid"),
        "LiveAuction": lot.get("live_auction"),
        "AuctionEndTime": lot.get("auction_end_time"),
        "MediaCount": item.get("media_quantity"),
        "ImageURLs": ";".join(image_url(m["uuid"]) for m in media if m.get("uuid")),
    }


def auction_month_year(lots):
    months = [lot["AuctionEndTime"][:7] for lot in lots if lot.get("AuctionEndTime")]
    return Counter(months).most_common(1)[0][0] if months else "unknown-date"


def scrape_all():
    auction = get_default_auction()
    auction_id = auction["id"]
    print(f"Scraping auction {auction_id} ({auction['title']})...")

    raw_lots = get_all_lots(auction_id)
    print(f"Collected {len(raw_lots)} lots")

    flattened = [flatten_lot(lot) for lot in raw_lots]
    month_year = auction_month_year(flattened)
    output_csv = f"{OUTPUT_DIR}/{FILENAME_PREFIX}_{month_year}.csv"

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(flattened)

    print(f"Wrote {len(flattened)} lots to {output_csv}")
    return output_csv, flattened


if __name__ == "__main__":
    scrape_all()
