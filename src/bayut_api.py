from __future__ import annotations

from typing import Any

import httpx


class BayutAlgoliaError(Exception):
    """Raised when the Bayut Algolia request fails."""


# Fields that are useful for the ECES dataset and are currently available
# from the Bayut Algolia listing index.
#
# description / description_l1 are kept here because Bayut advertises them
# in its index configuration, but the current index may return them as None.
ATTRIBUTES_TO_RETRIEVE = [
    # Identity
    "id",
    "objectID",
    "externalID",

    # Group A
    "purpose",
    "price",
    "rentFrequency",
    "title",
    "title_l1",
    "location",
    "category",
    "rooms",
    "baths",
    "area",
    "agency",
    "isVerified",
    "createdAt",

    # Text fields
    "description",
    "description_l1",

    # Structured information useful for Group B
    "amenities",
    "amenities_l1",
    "completionStatus",
    "furnishingStatus",
    "extraFields",
    "paymentPlans",
    "paymentPlanSummaries",
    "downPayment",
    "project",
    "offplanDetails",
    "plotArea",

    # Useful for identification / analysis
    "keywords",
    "keywords_l1",
    "slug",
    "slug_l1",
]


class BayutAlgoliaClient:
    """
    Client for Bayut's browser-facing Algolia search index.

    Algolia is currently the primary collection source because it provides
    stable listing records without requiring access to Bayut's CAPTCHA-
    protected HTML pages.
    """

    def __init__(
        self,
        app_id: str,
        api_key: str,
        index_name: str,
        timeout: float = 30.0,
    ) -> None:
        if not app_id:
            raise ValueError("Algolia application ID is required.")

        if not api_key:
            raise ValueError("Algolia API key is required.")

        if not index_name:
            raise ValueError("Algolia index name is required.")

        self.app_id = app_id
        self.api_key = api_key
        self.index_name = index_name

        self.client = httpx.Client(
            timeout=timeout,
            headers={
                "X-Algolia-Application-Id": app_id,
                "X-Algolia-API-Key": api_key,
                "Content-Type": "application/json",
            },
        )

        self.search_url = (
            f"https://{app_id.lower()}-dsn.algolia.net"
            f"/1/indexes/{index_name}/query"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self.client.close()

    def __enter__(self) -> "BayutAlgoliaClient":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc: Any,
        tb: Any,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        *,
        page: int = 0,
        hits_per_page: int = 24,
        filters: str | None = None,
    ) -> dict[str, Any]:
        """
        Query the Bayut Algolia index.

        Args:
            page:
                Zero-based Algolia page number.

            hits_per_page:
                Number of listings requested per page.

            filters:
                Optional Algolia filter expression.

        Returns:
            Raw Algolia response dictionary.
        """
        if page < 0:
            raise ValueError("page must be >= 0.")

        if not 1 <= hits_per_page <= 1000:
            raise ValueError(
                "hits_per_page must be between 1 and 1000."
            )

        payload: dict[str, Any] = {
            "page": page,
            "hitsPerPage": hits_per_page,
            "attributesToRetrieve": ATTRIBUTES_TO_RETRIEVE,
        }

        if filters:
            payload["filters"] = filters

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.client.post(
                    self.search_url,
                    json=payload,
                )
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            return data
                    except ValueError as exc:
                        raise BayutAlgoliaError("Algolia returned invalid JSON.") from exc

                last_error = BayutAlgoliaError(
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )
            except (httpx.HTTPError, httpx.RemoteProtocolError, Exception) as exc:
                last_error = exc

            import time
            time.sleep(1.0 * (attempt + 1))

        raise BayutAlgoliaError(f"Algolia request failed after 3 attempts: {last_error}")

    # ------------------------------------------------------------------
    # Listing access
    # ------------------------------------------------------------------

    def get_hits(
        self,
        *,
        page: int = 0,
        hits_per_page: int = 24,
        filters: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return only the listing records from a search response.
        """
        data = self.search(
            page=page,
            hits_per_page=hits_per_page,
            filters=filters,
        )

        hits = data.get("hits", [])

        if not isinstance(hits, list):
            raise BayutAlgoliaError(
                "Algolia response does not contain a valid hits list."
            )

        return [
            hit
            for hit in hits
            if isinstance(hit, dict)
        ]

    def total_hits(
        self,
        *,
        filters: str | None = None,
    ) -> int:
        """
        Return the total number of matching records.

        This performs a small search and reads Algolia's nbHits value.
        """
        data = self.search(
            page=0,
            hits_per_page=1,
            filters=filters,
        )

        value = data.get("nbHits")

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        return 0

    # ------------------------------------------------------------------
    # Convenience searches
    # ------------------------------------------------------------------

    def get_sale_hits(
        self,
        *,
        page: int = 0,
        hits_per_page: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Retrieve sale listings.
        """
        return self.get_hits(
            page=page,
            hits_per_page=hits_per_page,
            filters='purpose:"for-sale"',
        )

    def get_rent_hits(
        self,
        *,
        page: int = 0,
        hits_per_page: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Retrieve rental listings.
        """
        return self.get_hits(
            page=page,
            hits_per_page=hits_per_page,
            filters='purpose:"for-rent"',
        )

    def count_sale_listings(self) -> int:
        """
        Count available sale listings.
        """
        return self.total_hits(
            filters='purpose:"for-sale"',
        )

    def count_rent_listings(self) -> int:
        """
        Count available rental listings.
        """
        return self.total_hits(
            filters='purpose:"for-rent"',
        )