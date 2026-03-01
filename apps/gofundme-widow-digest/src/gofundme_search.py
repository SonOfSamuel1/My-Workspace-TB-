"""Search GoFundMe campaigns via Algolia API."""

import time
import requests


ALGOLIA_SEARCH_URL = "https://{app_id}-dsn.algolia.net/1/indexes/{index}/query"
GOFUNDME_CAMPAIGN_URL = "https://www.gofundme.com/f/{slug}"


def search_campaigns(config):
    """Search GoFundMe for widow-related campaigns using multiple queries.

    Returns deduplicated list of campaigns matching the filter criteria.
    """
    algolia_cfg = config["algolia"]
    filters_cfg = config["filters"]
    search_queries = config["search_queries"]

    url = ALGOLIA_SEARCH_URL.format(
        app_id=algolia_cfg["app_id"],
        index=algolia_cfg["index"],
    )
    headers = {
        "X-Algolia-API-Key": algolia_cfg["api_key"],
        "X-Algolia-Application-Id": algolia_cfg["app_id"],
        "Content-Type": "application/json",
    }

    cutoff_ts = int(time.time()) - (filters_cfg["max_age_days"] * 86400)
    seen_ids = set()
    campaigns = []

    for query in search_queries:
        algolia_filters = _build_algolia_filters(filters_cfg, cutoff_ts)
        payload = {
            "query": query,
            "hitsPerPage": filters_cfg["hits_per_query"],
            "filters": algolia_filters,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

        for hit in hits:
            obj_id = hit.get("objectID")
            if obj_id in seen_ids:
                continue
            seen_ids.add(obj_id)

            campaign = _parse_campaign(hit)
            if campaign and _passes_filters(campaign, filters_cfg):
                campaigns.append(campaign)

    # Sort by donation count descending (most active first)
    campaigns.sort(key=lambda c: c["donation_count"], reverse=True)
    return campaigns


def _build_algolia_filters(filters_cfg, cutoff_ts):
    """Build Algolia numeric/facet filter string."""
    parts = [
        f"created_at >= {cutoff_ts}",
        f"goalamount >= {filters_cfg['min_goal_amount'] * 100}",  # cents
        "status = 1",  # active campaigns only
    ]
    countries = filters_cfg.get("countries", [])
    if countries:
        country_filters = " OR ".join(f'country:"{c}"' for c in countries)
        parts.append(f"({country_filters})")
    return " AND ".join(parts)


def _parse_campaign(hit):
    """Extract relevant fields from an Algolia hit."""
    slug = hit.get("url", "")
    if not slug:
        return None

    goal = hit.get("goalamount", 0)
    raised = hit.get("realbalance", 0) or hit.get("balance", 0)
    currency = hit.get("currencycode", "USD")

    return {
        "id": hit.get("objectID"),
        "title": hit.get("fundname", "").strip(),
        "description": (hit.get("funddescription_cleaned", "") or "").strip()[:300],
        "url": GOFUNDME_CAMPAIGN_URL.format(slug=slug),
        "goal": goal / 100 if currency == "USD" else goal,
        "raised": raised / 100 if currency == "USD" else raised,
        "currency": currency,
        "donation_count": hit.get("donation_count", 0) or hit.get("donation_count_full", 0),
        "organizer": hit.get("username", ""),
        "city": hit.get("city", ""),
        "state": hit.get("state", ""),
        "country": hit.get("country", ""),
        "created_at": hit.get("created_at", 0),
        "thumbnail": hit.get("thumb_img_url", ""),
    }


def _passes_filters(campaign, filters_cfg):
    """Apply additional filters beyond what Algolia handles."""
    currencies = filters_cfg.get("currencies", [])
    if currencies and campaign["currency"] not in currencies:
        return False
    # Filter out campaigns with suspiciously high goals (likely spam)
    if campaign["goal"] > 5_000_000:
        return False
    return True
