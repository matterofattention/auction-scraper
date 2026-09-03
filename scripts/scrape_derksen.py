#!/usr/bin/env python3
"""Scrape the full Derksen auction house online catalogue into a single CSV.

Data source: https://derksen.cloudcatalogus.nl/Home/Catalog (AngularJS app).
The lot data itself comes from a plain JSON endpoint:
  Data/GetCatalog/?page={page}&AuctSessionID={id}&Search=&fIsAfterSale=false&Sort=1
Each page returns a JSON array of lots plus a trailing "summary" row
(GoedID is null) whose "Items" field holds the total lot count for that
AuctSessionID. The list of sessions ("Zittingen") is available at
Data/GetSessions.
"""

import csv
import time

import requests

BASE_URL = "https://derksen.cloudcatalogus.nl"
SESSIONS_URL = f"{BASE_URL}/Data/GetSessions"
CATALOG_URL = f"{BASE_URL}/Data/GetCatalog/"
REQUEST_DELAY_SECONDS = 0.5
OUTPUT_CSV = "data/derksen_catalog.csv"

session = requests.Session()


def get_sessions():
    response = session.get(SESSIONS_URL, timeout=30)
    response.raise_for_status()
    return response.json()


def get_catalog_page(auct_session_id, page):
    params = {
        "page": page,
        "AuctSessionID": auct_session_id,
        "Search": "",
        "fIsAfterSale": "false",
        "Sort": 1,
    }
    response = session.get(CATALOG_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def scrape_session(auct_session_id, session_name):
    lots = []
    total_items = None
    page = 1

    while True:
        rows = get_catalog_page(auct_session_id, page)
        real_lots = [row for row in rows if row.get("GoedID") is not None]
        summary_rows = [row for row in rows if row.get("GoedID") is None]

        if summary_rows and summary_rows[0].get("Items") is not None:
            total_items = summary_rows[0]["Items"]

        if not real_lots:
            break

        lots.extend(real_lots)
        print(
            f"  [{session_name} ({auct_session_id})] page {page}: "
            f"+{len(real_lots)} lots ({len(lots)}/{total_items or '?'})"
        )

        if total_items is not None and len(lots) >= total_items:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return lots


def main():
    sessions = get_sessions()
    print(f"Found {len(sessions)} sessions: "
          f"{[(s['ID'], s['Name']) for s in sessions]}")

    all_lots = []
    for auct_session in sessions:
        auct_session_id = auct_session["ID"]
        session_name = auct_session["Name"]
        print(f"Scraping session {auct_session_id} ({session_name})...")
        lots = scrape_session(auct_session_id, session_name)
        print(f"  -> collected {len(lots)} lots")
        all_lots.extend(lots)
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Total lots collected across all sessions: {len(all_lots)}")

    fieldnames = []
    for lot in all_lots:
        for key in lot.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_lots)

    print(f"Wrote {len(all_lots)} lots to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
