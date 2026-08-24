"""
Batch pre-fetcher for all discovered candidate listings in the dataset.
Fetches and caches full HTML detail pages into data/raw/details/<listing_id>.html.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config import DATASET_JSONL, RAW_DIR
from src.detail_fetcher import detail_fetcher


def main() -> None:
    if not DATASET_JSONL.exists():
        print(f"Dataset file {DATASET_JSONL} not found.")
        return

    with open(DATASET_JSONL, "r", encoding="utf-8") as f:
        listings = [json.loads(line) for line in f]

    print(f"Loaded {len(listings)} candidate listings from {DATASET_JSONL.name}.")
    details_dir = RAW_DIR / "details"
    details_dir.mkdir(parents=True, exist_ok=True)

    missing = []
    for item in listings:
        lid = str(item.get("listing_id") or item.get("externalID") or item.get("id"))
        target = details_dir / f"{lid}.html"
        if not target.exists() or target.stat().st_size < 20000:
            missing.append(item)

    print(f"Detail pages status: {len(listings) - len(missing)} already cached, {len(missing)} need download.")

    if not missing:
        print("All detail pages are already cached! Done.")
        return

    print(f"Starting concurrent download of {len(missing)} detail pages (max_workers=5)...")
    fetcher = detail_fetcher
    fetcher.max_workers = 5
    fetcher.delay_between_requests = 0.15

    def progress(done: int, total: int, stats: dict[str, int]) -> None:
        if done % 25 == 0 or done == total:
            pct = (done / total) * 100
            print(f"  ▶ [{done:3d}/{total:3d}] ({pct:5.1f}%) — Downloaded: {stats['fetched']}, Failed: {stats['failed']}")

    stats = fetcher.fetch_batch(missing, progress_callback=progress)
    print("\nBatch Download Summary:")
    print(f"  Total Requested: {stats['total']}")
    print(f"  Successfully Fetched: {stats['fetched']}")
    print(f"  Already Cached: {stats['cached']}")
    print(f"  Failed / Inaccessible: {stats['failed']}")


if __name__ == "__main__":
    main()
