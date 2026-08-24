"""
Stage 2 Detail Page Scraper & Cache Manager.

Retrieves raw HTML detail pages for discovered candidate listings,
persisting them to data/raw/details/<listing_id>.html for offline NLP extraction.
Maintains failure records in SQLite for failure_log.csv transparency.
"""

from __future__ import annotations

import concurrent.futures
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from src.config import DB_PATH, RAW_DIR
from src.db import Database

DETAILS_DIR = RAW_DIR / "details"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.bayut.eg/",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


class DetailPageFetcher:
    """
    High-throughput, polite HTTP detail-page fetcher with caching and failure logging.
    """

    def __init__(
        self,
        db: Database | None = None,
        max_workers: int = 4,
        timeout: float = 12.0,
        delay_between_requests: float = 0.3,
    ) -> None:
        self.db = db or Database(DB_PATH)
        self.max_workers = max_workers
        self.timeout = timeout
        self.delay_between_requests = delay_between_requests
        DETAILS_DIR.mkdir(parents=True, exist_ok=True)

    def fetch_listing(self, listing_id: str, url: str) -> tuple[bool, str]:
        """
        Fetch and cache a single detail page.
        Returns (success: bool, message: str).
        """
        target_file = DETAILS_DIR / f"{listing_id}.html"

        # If already cached and valid size (>20KB), skip
        if target_file.exists() and target_file.stat().st_size > 20000:
            return True, "already_cached"

        # Construct canonical ASCII URL to prevent Unicode URL encoding errors
        canonical_url = url
        if not canonical_url or not canonical_url.startswith("http"):
            canonical_url = f"https://www.bayut.eg/en/property/details-{listing_id}.html"
        elif any(ord(c) > 127 for c in canonical_url):
            # Extract numeric property ID or quote non-ASCII characters
            match = re.search(r"(\d{7,12})", canonical_url)
            if match:
                canonical_url = f"https://www.bayut.eg/en/property/details-{match.group(1)}.html"
            else:
                canonical_url = urllib.parse.quote(canonical_url, safe=":/?#[]@!$&'()*+,;=")

        req = urllib.request.Request(canonical_url, headers=DEFAULT_HEADERS)
        try:
            time.sleep(self.delay_between_requests)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                html_bytes = resp.read()
                html = html_bytes.decode("utf-8", errors="ignore")

                # Basic validation
                if resp.status == 200 and len(html) > 15000:
                    with open(target_file, "wb") as f:
                        f.write(html_bytes)
                    return True, f"fetched_{len(html_bytes)}_bytes"
                else:
                    self.db.log_failure(
                        listing_id=listing_id,
                        url=canonical_url,
                        stage="detail_fetch",
                        error_type="short_html",
                        error_message=f"Received short HTML response ({len(html)} bytes)",
                    )
                    return False, f"short_response_{len(html)}"

        except urllib.error.HTTPError as e:
            self.db.log_failure(
                listing_id=listing_id,
                url=url,
                stage="detail_fetch",
                error_type=f"http_{e.code}",
                error_message=f"HTTP Error {e.code}: {e.reason}",
            )
            return False, f"http_{e.code}"
        except Exception as e:
            self.db.log_failure(
                listing_id=listing_id,
                url=url,
                stage="detail_fetch",
                error_type="network_error",
                error_message=str(e),
            )
            return False, f"error_{e}"

    def fetch_batch(
        self,
        listings: list[dict[str, Any]],
        progress_callback: Any = None,
    ) -> dict[str, int]:
        """
        Fetch detail pages for a batch of candidate listings concurrently.
        """
        results = {"total": len(listings), "cached": 0, "fetched": 0, "failed": 0}
        total = len(listings)

        def _worker(item: dict[str, Any]):
            lid = str(item.get("listing_id") or item.get("externalID") or item.get("objectID") or item.get("id"))
            u = item.get("url") or f"https://www.bayut.eg/en/property/details-{lid}.html"
            ok, msg = self.fetch_listing(lid, u)
            return lid, ok, msg

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_id = {executor.submit(_worker, item): item for item in listings}
            completed = 0
            for future in concurrent.futures.as_completed(future_to_id):
                completed += 1
                try:
                    lid, ok, msg = future.result()
                    if ok:
                        if msg == "already_cached":
                            results["cached"] += 1
                        else:
                            results["fetched"] += 1
                    else:
                        results["failed"] += 1
                except Exception:
                    results["failed"] += 1

                if progress_callback:
                    progress_callback(completed, total, results)

        return results


detail_fetcher = DetailPageFetcher()
