from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from src.config import RAW_DIR
from src.db import Database, ListingRecord


class BrowserCollectorError(Exception):
    """Raised when browser collection cannot continue."""


class BayutCDPCollector:
    """
    Collect Bayut detail pages through an already-running Chrome session.

    Chrome must be started separately with remote debugging enabled, e.g.:

        chrome.exe --remote-debugging-port=9222

    This collector does not attempt to bypass CAPTCHA.

    Workflow:

        SQLite pending listing
            -> existing Chrome session
            -> navigate to detail URL
            -> detect CAPTCHA/challenge
            -> save valid HTML
            -> update SQLite
    """

    DETAILS_DIR = RAW_DIR / "details"

    def __init__(
        self,
        db: Database,
        *,
        cdp_url: str = "http://127.0.0.1:9222",
        wait_after_navigation_ms: int = 3000,
        navigation_timeout_ms: int = 30000,
        delay_between_pages: float = 2.0,
    ) -> None:
        self.db = db
        self.cdp_url = cdp_url
        self.wait_after_navigation_ms = wait_after_navigation_ms
        self.navigation_timeout_ms = navigation_timeout_ms
        self.delay_between_pages = delay_between_pages

        self.DETAILS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """
        Connect to the existing Chrome instance through CDP.
        """
        if self._playwright is not None:
            return

        self._playwright = sync_playwright().start()

        try:
            self._browser = (
                self._playwright.chromium.connect_over_cdp(
                    self.cdp_url
                )
            )
        except Exception as exc:
            self._playwright.stop()
            self._playwright = None

            raise BrowserCollectorError(
                "Could not connect to Chrome through CDP. "
                "Make sure Chrome is running with "
                "--remote-debugging-port=9222."
            ) from exc

        contexts = self._browser.contexts

        if not contexts:
            raise BrowserCollectorError(
                "Connected to Chrome, but no browser context exists."
            )

        self._context = contexts[0]

    def close(self) -> None:
        """
        Disconnect from Playwright.

        The existing Chrome browser is not closed by this method.
        """
        self._context = None
        self._browser = None

        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None

    def __enter__(self) -> "BayutCDPCollector":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect_pending(
        self,
        *,
        limit: int | None = None,
    ) -> dict[str, int]:
        """
        Process pending SQLite listings.

        Failed records are also retried because Database.get_pending_listings()
        includes status='failed'.
        """
        if self._context is None:
            self.connect()

        pending = self.db.get_pending_listings(
            limit=limit
        )

        successful = 0
        captcha = 0
        failed = 0
        skipped = 0

        print(
            f"[QUEUE] pending={len(pending)}"
        )

        for listing in pending:
            result = self._process_listing(
                listing
            )

            status = result["status"]

            if status == "saved":
                successful += 1

            elif status == "captcha":
                captcha += 1

            elif status == "skipped":
                skipped += 1

            else:
                failed += 1

            if self.delay_between_pages > 0:
                time.sleep(
                    self.delay_between_pages
                )

        return {
            "pending": len(pending),
            "successful": successful,
            "captcha": captcha,
            "failed": failed,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # Single listing
    # ------------------------------------------------------------------

    def _process_listing(
        self,
        listing: ListingRecord,
    ) -> dict[str, Any]:
        """
        Navigate to one listing and save valid HTML.
        """
        external_id = self._extract_external_id(
            listing.url
        )

        if external_id is None:
            message = (
                "Could not extract externalID "
                "from listing URL."
            )

            self.db.mark_failed(
                listing.listing_id,
                message,
            )

            print(
                f"[FAILED] {listing.listing_id}: "
                f"{message}"
            )

            return {
                "status": "failed",
                "reason": message,
            }

        output_path = (
            self.DETAILS_DIR
            / f"{external_id}.html"
        )

        # Idempotency:
        # never overwrite an already-valid saved page.
        if output_path.exists():
            validation = (
                self._validate_saved_html(
                    output_path
                )
            )

            if validation["valid"]:
                self.db.update_status(
                    listing.listing_id,
                    "fetched",
                    raw_html_path=str(
                        output_path
                    ),
                    error_message=None,
                )

                print(
                    f"[SKIP] {listing.listing_id} "
                    f"already saved: {external_id}"
                )

                return {
                    "status": "skipped",
                    "path": str(output_path),
                }

        self.db.update_status(
            listing.listing_id,
            "fetching",
            error_message=None,
        )

        page = self._get_page()

        try:
            print(
                f"[OPEN] {listing.listing_id} "
                f"{listing.url}"
            )

            page.goto(
                listing.url,
                wait_until="domcontentloaded",
                timeout=self.navigation_timeout_ms,
            )

            if self.wait_after_navigation_ms > 0:
                page.wait_for_timeout(
                    self.wait_after_navigation_ms
                )

            current_url = page.url

            html = page.content()

            if self._is_captcha_page(
                page,
                html,
            ):
                message = (
                    "CAPTCHA/challenge page detected."
                )

                self.db.mark_failed(
                    listing.listing_id,
                    message,
                )

                print(
                    f"[CAPTCHA] "
                    f"{listing.listing_id} "
                    f"{current_url}"
                )

                return {
                    "status": "captcha",
                    "reason": message,
                }

            validation = (
                self._validate_html_content(
                    html
                )
            )

            if not validation["valid"]:
                message = validation["reason"]

                self.db.mark_failed(
                    listing.listing_id,
                    message,
                )

                print(
                    f"[INVALID] "
                    f"{listing.listing_id}: "
                    f"{message}"
                )

                return {
                    "status": "failed",
                    "reason": message,
                }

            output_path.write_text(
                html,
                encoding="utf-8",
            )

            self.db.update_status(
                listing.listing_id,
                "fetched",
                raw_html_path=str(
                    output_path
                ),
                error_message=None,
            )

            print(
                f"[SAVED] "
                f"{listing.listing_id} "
                f"-> {output_path}"
            )

            return {
                "status": "saved",
                "path": str(output_path),
            }

        except PlaywrightTimeoutError:
            message = (
                f"Navigation timeout: {listing.url}"
            )

            self.db.mark_failed(
                listing.listing_id,
                message,
            )

            print(
                f"[TIMEOUT] {listing.listing_id}"
            )

            return {
                "status": "failed",
                "reason": message,
            }

        except Exception as exc:
            message = (
                f"{type(exc).__name__}: {exc}"
            )

            self.db.mark_failed(
                listing.listing_id,
                message,
            )

            print(
                f"[FAILED] {listing.listing_id}: "
                f"{message}"
            )

            return {
                "status": "failed",
                "reason": message,
            }

        finally:
            try:
                page.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Browser/page helpers
    # ------------------------------------------------------------------

    def _get_page(self) -> Page:
        if self._context is None:
            raise BrowserCollectorError(
                "Browser context is not connected."
            )

        page = self._context.new_page()

        page.set_default_timeout(
            self.navigation_timeout_ms
        )

        return page

    # ------------------------------------------------------------------
    # CAPTCHA detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_captcha_page(
        page: Page,
        html: str,
    ) -> bool:
        """
        Detect strong Bayut challenge indicators.
        """
        lowered = html.lower()

        indicators = (
            "captchachallenge",
            "كلمة التحقق",
            "يرجى التحقق من هويتك",
            "captcha challenge",
            "verify you are human",
            "checking your browser",
            "access denied",
        )

        if any(
            indicator in lowered
            for indicator in indicators
        ):
            return True

        try:
            title = page.title().lower()

            if (
                "كلمة التحقق" in title
                or "captcha" in title
            ):
                return True

        except Exception:
            pass

        return False

    # ------------------------------------------------------------------
    # HTML validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_html_content(
        html: str,
    ) -> dict[str, Any]:
        """
        Lightweight validation before saving.

        We intentionally do not require a description because some valid
        Bayut listings may have no description.
        """
        if not html.strip():
            return {
                "valid": False,
                "reason": "HTML is empty.",
            }

        lowered = html.lower()

        challenge_indicators = (
            "captchachallenge",
            "كلمة التحقق",
            "يرجى التحقق من هويتك",
            "captcha challenge",
            "verify you are human",
            "checking your browser",
            "access denied",
        )

        if any(
            indicator in lowered
            for indicator in challenge_indicators
        ):
            return {
                "valid": False,
                "reason": "CAPTCHA/challenge page.",
            }

        if "dataLayer" not in html:
            return {
                "valid": False,
                "reason": "Bayut dataLayer not found.",
            }

        return {
            "valid": True,
        }

    def _validate_saved_html(
        self,
        path: Path,
    ) -> dict[str, Any]:
        try:
            html = path.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            return {
                "valid": False,
                "reason": str(exc),
            }

        return self._validate_html_content(
            html
        )

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_external_id(
        url: str,
    ) -> str | None:
        """
        Extract the public Bayut externalID from:

            /تفاصيل-503972548/العقار.html
        """
        decoded = unquote(
            urlparse(url).path
        )

        match = re.search(
            r"تفاصيل-(\d+)",
            decoded,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        # Fallback for any numeric detail URL.
        match = re.search(
            r"(?:details-|property/)(\d+)",
            decoded,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return None