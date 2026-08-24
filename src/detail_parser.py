from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup


class DetailParserError(Exception):
    """Raised when a Bayut detail page cannot be parsed."""


class BayutDetailParser:
    """
    Parse a saved Bayut individual-listing HTML page.

    This parser operates entirely offline. It does not make HTTP requests
    and does not interact with Bayut's CAPTCHA system.

    It extracts:
        - original listing description
        - title
        - canonical URL
        - embedded Bayut dataLayer fields
    """

    DESCRIPTION_SELECTOR = '[aria-label="وصف العقار"]'

    def parse_html(
        self,
        html: str,
    ) -> dict[str, Any]:
        if not html.strip():
            raise DetailParserError("HTML is empty.")

        soup = BeautifulSoup(
            html,
            "lxml",
        )

        data_layer = self._extract_data_layer(soup)

        return {
            # Core source fields
            "description_raw": self._extract_description(soup),
            "title": self._extract_title(soup),
            "canonical_url": self._extract_canonical_url(soup),

            # Supplemental metadata
            "meta_description": self._extract_meta_description(soup),

            # Embedded Bayut data
            "listing_id": self._first_value(
                data_layer,
                (
                    "listing_id",
                    "object_id",
                    "objectID",
                ),
            ),

            "purpose": self._first_value(
                data_layer,
                (
                    "purpose",
                ),
            ),

            "completion_status": self._first_value(
                data_layer,
                (
                    "completion_status",
                    "completionStatus",
                ),
            ),

            "property_type": self._first_value(
                data_layer,
                (
                    "property_type",
                    "propertyType",
                ),
            ),

            "price": self._to_number(
                self._first_value(
                    data_layer,
                    (
                        "property_price",
                        "price",
                    ),
                )
            ),

            "area_sqm": self._to_number(
                self._first_value(
                    data_layer,
                    (
                        "property_area",
                        "area",
                    ),
                )
            ),

            "bedrooms": self._extract_bedrooms(
                data_layer
            ),

            "bathrooms": self._extract_bathrooms(
                data_layer
            ),

            "governorate": self._clean_location(
                self._first_value(
                    data_layer,
                    (
                        "loc_1_name",
                    ),
                )
            ),

            "city": self._clean_location(
                self._first_value(
                    data_layer,
                    (
                        "loc_city_name",
                        "loc_2_name",
                    ),
                )
            ),

            "district": self._clean_location(
                self._first_value(
                    data_layer,
                    (
                        "loc_neighbourhood_name",
                        "loc_name",
                        "loc_3_name",
                    ),
                )
            ),

            "agency_id": self._first_value(
                data_layer,
                (
                    "agency_id",
                    "agencyid",
                ),
            ),

            "agent_id": self._first_value(
                data_layer,
                (
                    "agent_id",
                ),
            ),

            "listing_state": self._first_value(
                data_layer,
                (
                    "listing_state",
                ),
            ),

            "page_language": self._first_value(
                data_layer,
                (
                    "language",
                ),
            ),

            # Useful evidence retained for later parsing.
            "data_layer": data_layer,
        }

    def parse_file(
        self,
        path: str,
    ) -> dict[str, Any]:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            html = file.read()

        return self.parse_html(html)

    # ==================================================================
    # Description
    # ==================================================================

    DESCRIPTION_SELECTORS = (
        '[aria-label="Property description"]',
        '[aria-label="وصف العقار"]',
        '[aria-label*="description"]',
        '[aria-label*="وصف"]',
        'div[class*="description"]',
        'div[class*="Description"]',
        'div[data-testid*="description"]',
    )

    def _extract_description(
        self,
        soup: BeautifulSoup,
    ) -> str | None:
        for selector in self.DESCRIPTION_SELECTORS:
            element = soup.select_one(selector)
            if element is not None:
                cleaned = self._clean_description(element)
                if cleaned and len(cleaned) > 20:
                    return cleaned

        return None

    @staticmethod
    def _clean_description(
        element: Any,
    ) -> str | None:
        """
        Preserve the original wording.

        Only HTML <br> elements are converted to newline characters.
        No linguistic normalization is performed here.
        """
        for br in element.find_all("br"):
            br.replace_with("\n")

        text = element.get_text(
            separator="",
        )

        text = text.strip()

        return text or None

    # ==================================================================
    # Title
    # ==================================================================

    @staticmethod
    def _extract_title(
        soup: BeautifulSoup,
    ) -> str | None:
        title_element = soup.find("h1")

        if title_element is not None:
            title = title_element.get_text(
                " ",
                strip=True,
            )

            if title:
                return title

        document_title = soup.find("title")

        if document_title is None:
            return None

        title = document_title.get_text(
            " ",
            strip=True,
        )

        title = re.sub(
            r"\s*\|\s*Bayut\s+Egypt\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()

        return title or None

    # ==================================================================
    # Canonical URL
    # ==================================================================

    @staticmethod
    def _extract_canonical_url(
        soup: BeautifulSoup,
    ) -> str | None:
        link = soup.find(
            "link",
            rel="canonical",
        )

        if link is None:
            return None

        href = link.get("href")

        if not isinstance(href, str):
            return None

        return href.strip() or None

    # ==================================================================
    # Meta description
    # ==================================================================

    @staticmethod
    def _extract_meta_description(
        soup: BeautifulSoup,
    ) -> str | None:
        for attribute in (
            {"name": "description"},
            {"property": "og:description"},
            {"property": "twitter:description"},
        ):
            element = soup.find(
                "meta",
                attrs=attribute,
            )

            if element is None:
                continue

            content = element.get("content")

            if isinstance(content, str) and content.strip():
                return content.strip()

        return None

    # ==================================================================
    # Embedded dataLayer
    # ==================================================================

    @staticmethod
    def _extract_data_layer(
        soup: BeautifulSoup,
    ) -> dict[str, Any]:
        scripts = soup.find_all("script")

        for script in scripts:
            script_text = script.string

            if not isinstance(script_text, str):
                continue

            if "dataLayer" not in script_text:
                continue

            if ".push(" not in script_text:
                continue

            parsed = BayutDetailParser._extract_json_from_push(
                script_text
            )

            if isinstance(parsed, dict):
                return parsed

        return {}

    @staticmethod
    def _extract_json_from_push(
        script_text: str,
    ) -> dict[str, Any] | None:
        marker_candidates = (
            "dataLayer'].push(",
            'dataLayer"].push(',
            "dataLayer.push(",
        )

        start_index = -1

        for marker in marker_candidates:
            index = script_text.find(marker)

            if index != -1:
                start_index = index + len(marker)
                break

        if start_index == -1:
            return None

        substring = script_text[start_index:].lstrip()

        decoder = json.JSONDecoder()

        try:
            value, _ = decoder.raw_decode(substring)
        except json.JSONDecodeError:
            return None

        if isinstance(value, dict):
            return value

        return None

    # ==================================================================
    # Embedded field helpers
    # ==================================================================

    @staticmethod
    def _first_value(
        data: dict[str, Any],
        keys: tuple[str, ...],
    ) -> Any:
        for key in keys:
            value = data.get(key)

            if value is not None:
                return value

        return None

    @staticmethod
    def _extract_bedrooms(
        data: dict[str, Any],
    ) -> int | None:
        values = data.get(
            "property_beds_list"
        )

        if isinstance(values, list) and values:
            return BayutDetailParser._to_int(
                values[0]
            )

        return BayutDetailParser._to_int(
            data.get("bedrooms")
        )

    @staticmethod
    def _extract_bathrooms(
        data: dict[str, Any],
    ) -> int | None:
        values = data.get(
            "property_baths_list"
        )

        if isinstance(values, list) and values:
            return BayutDetailParser._to_int(
                values[0]
            )

        return BayutDetailParser._to_int(
            data.get("bathrooms")
        )

    @staticmethod
    def _clean_location(
        value: Any,
    ) -> str | None:
        """
        Clean Bayut's semicolon-delimited location representation.

        Example:
            ";الإسكندرية;" -> "الإسكندرية"
        """
        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value:
            return None

        # Bayut uses semicolon-delimited location strings.
        parts = [
            part.strip()
            for part in value.split(";")
            if part.strip()
        ]

        if not parts:
            return None

        return " / ".join(dict.fromkeys(parts))

    # ==================================================================
    # Numeric helpers
    # ==================================================================

    @staticmethod
    def _to_number(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None