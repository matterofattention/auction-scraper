"""Shared scraping logic for auction houses hosted on the Artisio platform.

Each auction house embeds the Artisio Webapp widget (served from
cdn.artisio.co) on its own website. The widget authenticates itself to
Artisio's shared backend with an "ARTISIO-CLIENT-ID" header identifying
the auction house plus a matching "Origin" header for that auction
house's own domain, and reads catalogue data from a JSON REST API at
webapp.artisio.co:
  GET /website/auctions/timed?status=published&page={page}&limit={limit}
  GET /website/lots/?auction_uuid={uuid}&page={page}&limit={limit}
Both endpoints paginate (100 items max per page) and report the total
"count" alongside the page of results ("result" for auctions, "results"
for lots).
"""

import csv
import json
import time
from collections import Counter
from email.utils import parsedate_to_datetime

import requests

API_BASE = "https://webapp.artisio.co"
PAGE_SIZE = 100
REQUEST_DELAY_SECONDS = 0.5

session = requests.Session()


def _headers(site_origin, client_id):
    return {
        "ARTISIO-CLIENT-ID": client_id,
        "Origin": site_origin,
        "Accept": "application/json",
    }


def _localized(value, lang):
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or ""
    return value


def _get_paginated(path, site_origin, client_id, params, response_key, results_field, label):
    items = []
    page = 1

    while True:
        query = dict(params, page=page, limit=PAGE_SIZE)
        response = session.get(
            f"{API_BASE}/{path}",
            params=query,
            headers=_headers(site_origin, client_id),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()[response_key]
        batch = payload[results_field]

        if not batch:
            break

        items.extend(batch)
        total = payload["count"]
        print(f"  [{label}] page {page}: +{len(batch)} ({len(items)}/{total})")

        if len(items) >= total:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return items


def get_auctions(site_origin, client_id, status="published"):
    return _get_paginated(
        "website/auctions/timed",
        site_origin,
        client_id,
        {"status": status, "sort": "start_date", "sort-by": "asc"},
        response_key="auctions",
        results_field="result",
        label=f"auctions ({status})",
    )


def get_lots(site_origin, client_id, auction_uuid, auction_label):
    return _get_paginated(
        "website/lots/",
        site_origin,
        client_id,
        {"auction_uuid": auction_uuid, "sort": "lot_no", "sort-by": "asc"},
        response_key="lots",
        results_field="results",
        label=auction_label,
    )


def flatten_lot(lot, lang):
    category = lot.get("category") or {}
    currency = lot.get("currency") or {}
    winning_bid = lot.get("winning_bid") or {}
    images = lot.get("image_urls") or []
    dynamic_fields = (lot.get("dynamic_fields") or {}).get(lang) or {}

    return {
        "LotUUID": lot.get("uuid"),
        "LotNo": lot.get("lot_no"),
        "StockNo": lot.get("stock_no"),
        "AuctionUUID": lot.get("auction_uuid"),
        "AuctionNo": lot.get("auction_no"),
        "AuctionTitle": _localized(lot.get("auction_title"), lang),
        "Category": _localized(category.get("name"), lang),
        "Title": _localized(lot.get("title"), lang),
        "ShortDescription": _localized(lot.get("short_description"), lang),
        "Description": _localized(lot.get("description"), lang),
        "Status": lot.get("status"),
        "Currency": currency.get("code"),
        "LowEstimate": lot.get("low"),
        "HighEstimate": lot.get("high"),
        "StartPrice": lot.get("start_price"),
        "Reserve": lot.get("reserve"),
        "BuyNowPrice": lot.get("buy_now_price"),
        "Quantity": lot.get("quantity"),
        "NumOfBids": lot.get("num_of_bids"),
        "LastBidAmount": lot.get("last_bid_amount"),
        "WinningBidAmount": winning_bid.get("amount"),
        "IsStarted": lot.get("is_started"),
        "StartDate": lot.get("start_date"),
        "EndDate": lot.get("end_date"),
        "ImageURLs": ";".join(images),
        "NrOfImages": len(images),
        "DynamicFields": json.dumps(dynamic_fields, ensure_ascii=False) if dynamic_fields else "",
    }


def auction_month_year(lots):
    """Most common "YYYY-MM" among lots' `EndDate` field.

    An auction house can have several auctions closing in different
    months at once, so this picks the month/year shared by most lots as
    the catalogue's date (mirrors scrape_cloudcatalogus.auction_month_year).
    """
    months = []
    for lot in lots:
        end_date = lot.get("EndDate")
        if not end_date:
            continue
        try:
            dt = parsedate_to_datetime(end_date)
        except (TypeError, ValueError):
            continue
        months.append(f"{dt.year:04d}-{dt.month:02d}")
    return Counter(months).most_common(1)[0][0]


def scrape_all(site_origin, client_id, output_dir, filename_prefix, lang="nl", status="published"):
    print(f"Fetching {status} auctions from {site_origin}...")
    auctions = get_auctions(site_origin, client_id, status=status)
    print(
        f"Found {len(auctions)} {status} auctions: "
        f"{[(a['auction_no'], _localized(a['title'], lang)) for a in auctions]}"
    )

    all_lots = []
    for auction in auctions:
        auction_uuid = auction["uuid"]
        auction_no = auction["auction_no"]
        title = _localized(auction["title"], lang)
        print(f"Scraping auction {auction_no} ({title})...")
        lots = get_lots(site_origin, client_id, auction_uuid, f"{auction_no} {title}")
        flattened = [flatten_lot(lot, lang) for lot in lots]
        print(f"  -> collected {len(flattened)} lots")
        all_lots.extend(flattened)
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Total lots collected across all auctions: {len(all_lots)}")

    fieldnames = []
    for lot in all_lots:
        for key in lot.keys():
            if key not in fieldnames:
                fieldnames.append(key)

    output_csv = f"{output_dir}/{filename_prefix}_{auction_month_year(all_lots)}.csv"

    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_lots)

    print(f"Wrote {len(all_lots)} lots to {output_csv}")
    return output_csv, all_lots
