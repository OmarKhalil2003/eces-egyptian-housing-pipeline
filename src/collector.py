from __future__ import annotations

from pathlib import Path
from typing import Any

from src.bayut_api import BayutAlgoliaClient
from src.config import (
    ALGOLIA_APP_ID,
    ALGOLIA_SALE_INDEX,
    ALGOLIA_SEARCH_API_KEY,
    RAW_DIR,
    ensure_directories,
)
from src.db import Database
from src.detail_parser import BayutDetailParser


class CollectorError(Exception):
    """Raised when collection preparation or validation fails."""


class BayutCollector:
    """
    Prepare and validate Bayut detail-page collection.

    Important design decision:

    Bayut category/detail pages are protected against automated HTTP/browser
    access. Therefore this collector does NOT attempt to scrape Bayut HTML.

    Instead:

        1. Algolia provides scalable listing discovery.
        2. The collector stores listing metadata/checkpoints.
        3. A normal browser is used externally to save individual detail-page
           HTML files.
        4. This collector validates those saved files.
        5. Valid files are then ready for offline parsing.

    This keeps source acquisition separate from extraction.
    """

    DETAILS_DIR = RAW_DIR / "details"

    def __init__(
        self,
        db: Database,
        *,
        target_count: int = 550,
    ) -> None:
        self.db = db
        self.target_count = target_count

        ensure_directories()

        self.DETAILS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.algolia = BayutAlgoliaClient(
            ALGOLIA_APP_ID,
            ALGOLIA_SEARCH_API_KEY,
            ALGOLIA_SALE_INDEX,
        )

        self.detail_parser = BayutDetailParser()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the Algolia client."""
        self.algolia.close()

    def __enter__(self) -> "BayutCollector":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prepare_candidates(
        self,
        *,
        sale_count: int = 275,
        rent_count: int = 275,
        start_page: int = 0,
    ) -> dict[str, int]:
        """
        Pull candidate listings from Algolia and register them in SQLite.

        The method does not download Bayut HTML.

        Args:
            sale_count:
                Number of sale listings to register.

            rent_count:
                Number of rental listings to register.

            start_page:
                Zero-based Algolia page from which to begin.

        Returns:
            Summary of discovered and newly inserted records.
        """
        if sale_count < 0:
            raise ValueError(
                "sale_count must be >= 0."
            )

        if rent_count < 0:
            raise ValueError(
                "rent_count must be >= 0."
            )

        discovered = 0
        inserted = 0

        if sale_count:
            sale_result = self._prepare_purpose_candidates(
                purpose="sale",
                target_count=sale_count,
                start_page=start_page,
            )

            discovered += sale_result["discovered"]
            inserted += sale_result["inserted"]

        if rent_count:
            rent_result = self._prepare_purpose_candidates(
                purpose="rent",
                target_count=rent_count,
                start_page=start_page,
            )

            discovered += rent_result["discovered"]
            inserted += rent_result["inserted"]

        return {
            "discovered": discovered,
            "inserted": inserted,
            "db_records": self.db.count(),
        }

    def validate_saved_pages(
        self,
        *,
        limit: int | None = None,
    ) -> dict[str, int]:
        """
        Validate saved detail HTML files.

        A file is accepted only when it is actually a listing page and not
        a CAPTCHA/challenge page.

        Returns:
            Validation statistics.
        """
        validated = 0
        valid = 0
        captcha = 0
        invalid = 0
        missing = 0

        listings = self.db.get_pending_listings(
            limit=limit
        )

        # Also inspect records that may already have a stored HTML path.
        if not listings:
            listings = self.db.get_fetched_listings(
                limit=limit
            )

        for listing in listings:
            validated += 1

            raw_path = self._find_saved_html(
                listing.listing_id
            )

            if raw_path is None:
                missing += 1

                print(
                    f"[MISSING] {listing.listing_id}"
                )

                continue

            result = self.validate_html_file(
                raw_path
            )

            if result["status"] == "valid":
                valid += 1

                print(
                    f"[VALID] {listing.listing_id}"
                )

            elif result["status"] == "captcha":
                captcha += 1

                self._mark_validation_failure(
                    listing.listing_id,
                    "CAPTCHA/challenge page",
                )

                print(
                    f"[CAPTCHA] {listing.listing_id}"
                )

            else:
                invalid += 1

                self._mark_validation_failure(
                    listing.listing_id,
                    str(
                        result.get(
                            "reason",
                            "Invalid detail page",
                        )
                    ),
                )

                print(
                    f"[INVALID] {listing.listing_id}: "
                    f"{result.get('reason')}"
                )

        return {
            "validated": validated,
            "valid": valid,
            "captcha": captcha,
            "invalid": invalid,
            "missing": missing,
        }

    def validate_html_file(
        self,
        path: str | Path,
    ) -> dict[str, Any]:
        """
        Validate one saved HTML file.

        A valid listing page must:
            - contain HTML
            - not be a CAPTCHA/challenge page
            - contain a canonical URL
            - contain a listing ID
            - preferably contain description text

        Description is reported separately because some valid pages may
        legitimately have no description.
        """
        html_path = Path(path)

        if not html_path.exists():
            return {
                "status": "missing",
                "reason": "File does not exist.",
            }

        try:
            html = html_path.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            return {
                "status": "invalid",
                "reason": f"Could not read file: {exc}",
            }

        if not html.strip():
            return {
                "status": "invalid",
                "reason": "HTML file is empty.",
            }

        lowered = html.lower()

        if self._looks_like_captcha(
            lowered
        ):
            return {
                "status": "captcha",
                "reason": "CAPTCHA/challenge page detected.",
            }

        try:
            parsed = self.detail_parser.parse_html(
                html
            )
        except Exception as exc:
            return {
                "status": "invalid",
                "reason": (
                    f"Detail parser failed: {type(exc).__name__}: {exc}"
                ),
            }

        canonical_url = parsed.get(
            "canonical_url"
        )

        listing_id = parsed.get(
            "listing_id"
        )

        title = parsed.get(
            "title"
        )

        description = parsed.get(
            "description_raw"
        )

        if not canonical_url:
            return {
                "status": "invalid",
                "reason": "No canonical listing URL found.",
            }

        if not listing_id:
            return {
                "status": "invalid",
                "reason": "No listing ID found.",
            }

        if not title:
            return {
                "status": "invalid",
                "reason": "No listing title found.",
            }

        return {
            "status": "valid",
            "canonical_url": canonical_url,
            "listing_id": str(listing_id),
            "title": title,
            "description_present": bool(
                isinstance(
                    description,
                    str,
                )
                and description.strip()
            ),
        }

    # ------------------------------------------------------------------
    # Candidate preparation
    # ------------------------------------------------------------------

    def _prepare_purpose_candidates(
        self,
        *,
        purpose: str,
        target_count: int,
        start_page: int,
    ) -> dict[str, int]:
        """
        Retrieve enough Algolia records for one purpose.
        """
        discovered = 0
        inserted = 0

        page = start_page

        # Algolia can return up to 1000 records per request, but 100 keeps
        # responses manageable and makes checkpointing straightforward.
        hits_per_page = 100

        while discovered < target_count:
            if purpose == "sale":
                hits = self.algolia.get_sale_hits(
                    page=page,
                    hits_per_page=hits_per_page,
                )
            elif purpose == "rent":
                hits = self.algolia.get_rent_hits(
                    page=page,
                    hits_per_page=hits_per_page,
                )
            else:
                raise ValueError(
                    f"Unsupported purpose: {purpose}"
                )

            if not hits:
                break

            for raw in hits:
                if discovered >= target_count:
                    break

                listing_id = self._extract_listing_id(
                    raw
                )

                if listing_id is None:
                    continue

                external_id = self._extract_external_id(
                    raw
                )

                if external_id is None:
                    continue

                url = self.build_detail_url(
                    external_id
                )

                was_inserted = self.db.add_listing(
                    listing_id=listing_id,
                    url=url,
                    purpose=purpose,
                )

                if was_inserted:
                    inserted += 1

                discovered += 1

                print(
                    f"[CANDIDATE] "
                    f"purpose={purpose} "
                    f"listing_id={listing_id} "
                    f"external_id={external_id}"
                )

            page += 1

        return {
            "discovered": discovered,
            "inserted": inserted,
        }

    # ------------------------------------------------------------------
    # Listing identifiers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_listing_id(
        raw: dict[str, Any],
    ) -> str | None:
        """
        Use Algolia objectID as the stable internal identifier.

        Fallback:
            id -> externalID
        """
        for key in (
            "objectID",
            "id",
            "externalID",
        ):
            value = raw.get(key)

            if value is not None:
                value = str(value).strip()

                if value:
                    return value

        return None

    @staticmethod
    def _extract_external_id(
        raw: dict[str, Any],
    ) -> str | None:
        """
        externalID is the identifier used by Bayut's public detail URL.
        """
        value = raw.get(
            "externalID"
        )

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    # ------------------------------------------------------------------
    # Detail URLs
    # ------------------------------------------------------------------

    @staticmethod
    def build_detail_url(
        external_id: str,
    ) -> str:
        """
        Build the Arabic Bayut individual listing URL.
        """
        return (
            "https://www.bayut.eg/"
            f"تفاصيل-{external_id}/"
            "العقار.html"
        )

    # ------------------------------------------------------------------
    # Saved HTML discovery
    # ------------------------------------------------------------------

    def _find_saved_html(
        self,
        listing_id: str,
    ) -> Path | None:
        """
        Look for the preferred detail HTML filename.

        We support both:
            data/raw/details/<externalID>.html
            data/raw/<listing_id>.html

        The details directory is the preferred location.
        """
        candidates = (
            self.DETAILS_DIR
            / f"{listing_id}.html",
            RAW_DIR
            / f"{listing_id}.html",
        )

        for path in candidates:
            if path.exists():
                return path

        return None

    # ------------------------------------------------------------------
    # CAPTCHA validation
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_like_captcha(
        lowered_html: str,
    ) -> bool:
        """
        Detect Bayut challenge pages.

        This is intentionally conservative: detection means the page
        contains strong challenge indicators, not merely that Bayut uses
        anti-bot infrastructure somewhere in its scripts.
        """
        indicators = (
            "captchachallenge",
            "كلمة التحقق",
            "يرجى التحقق من هويتك",
            "captcha challenge",
            "verify you are human",
            "checking your browser",
            "access denied",
        )

        return any(
            indicator in lowered_html
            for indicator in indicators
        )

    # ------------------------------------------------------------------
    # Database validation state
    # ------------------------------------------------------------------

    def _mark_validation_failure(
        self,
        listing_id: str,
        message: str,
    ) -> None:
        """
        Mark a saved page as failed rather than fetched.

        This keeps the SQLite state honest and allows the file to be
        replaced later.
        """
        try:
            self.db.mark_failed(
                listing_id,
                message,
            )
        except Exception:
            # Validation should not crash the entire batch if the database
            # implementation does not support the desired transition.
            pass

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def count_saved_detail_pages(self) -> int:
        """
        Count saved HTML files in the preferred details directory.
        """
        return len(
            list(
                self.DETAILS_DIR.glob(
                    "*.html"
                )
            )
        )

    def list_saved_detail_pages(
        self,
    ) -> list[Path]:
        """
        Return saved detail HTML files sorted by filename.
        """
        return sorted(
            self.DETAILS_DIR.glob(
                "*.html"
            )
        )