"""Shared scraping logic for auction houses hosted on cloudcatalogus.nl.

Each auction house runs the same AngularJS app on its own subdomain
(e.g. derksen.cloudcatalogus.nl, medusa.cloudcatalogus.nl). The lot data
comes from a plain JSON endpoint:
  Data/GetCatalog/?page={page}&AuctSessionID={id}&Search=&fIsAfterSale=false&Sort=1
Each page returns a JSON array of lots plus a trailing "summary" row
(GoedID is null) whose "Items" field holds the total lot count for that
AuctSessionID. The list of sessions ("Zittingen") is available at
Data/GetSessions.
"""

import csv
import time

import requests

REQUEST_DELAY_SECONDS = 0.5

session = requests.Session()


def get_sessions(base_url):
    response = session.get(f"{base_url}/Data/GetSessions", timeout=30)
    response.raise_for_status()
    return response.json()


def get_catalog_page(base_url, auct_session_id, page):
    params = {
        "page": page,
        "AuctSessionID": auct_session_id,
        "Search": "",
        "fIsAfterSale": "false",
        "Sort": 1,
    }
    response = session.get(
        f"{base_url}/Data/GetCatalog/", params=params, timeout=30
    )
    response.raise_for_status()
    return response.json()


def scrape_session(base_url, auct_session_id, session_name):
    lots = []
    total_items = None
    page = 1

    while True:
        rows = get_catalog_page(base_url, auct_session_id, page)
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


def scrape_all(base_url, output_csv):
    sessions = get_sessions(base_url)
    print(f"Found {len(sessions)} sessions: "
          f"{[(s['ID'], s['Name']) for s in sessions]}")

    all_lots = []
    for auct_session in sessions:
        auct_session_id = auct_session["ID"]
        session_name = auct_session["Name"]
        print(f"Scraping session {auct_session_id} ({session_name})...")
        lots = scrape_session(base_url, auct_session_id, session_name)
        print(f"  -> collected {len(lots)} lots")
        all_lots.extend(lots)
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Total lots collected across all sessions: {len(all_lots)}")

    fieldnames = []
    for lot in all_lots:
        for key in lot.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_lots)

    print(f"Wrote {len(all_lots)} lots to {output_csv}")
    return all_lots
