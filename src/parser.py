from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models import HousingListing, RawBayutListing
from src.normalizer import normalize_text
from src.rules import ListingRulesParser


class BayutParser:
    """
    Merge Bayut Algolia data and saved detail-page data into the
    canonical HousingListing model.

    Source priority:

    1. Explicit detail-page data for fields directly present there.
    2. Explicit Algolia structured data.
    3. Deterministic rules applied to title, keywords, and description.
    4. None when the source does not support a value.

    No external knowledge is used to invent missing values.
    """

    def __init__(self) -> None:
        self.rules_parser = ListingRulesParser()

    # ==================================================================
    # Public API
    # ==================================================================

    def parse(
        self,
        raw: dict[str, Any] | RawBayutListing,
        detail: dict[str, Any] | None = None,
    ) -> HousingListing:
        """
        Convert one Algolia record, optionally enriched with a parsed
        Bayut detail page, into HousingListing.

        Args:
            raw:
                Raw Algolia listing.

            detail:
                Output of BayutDetailParser.parse_file() or parse_html().
                May be None when the detail page is not available.
        """
        if isinstance(raw, dict):
            source = RawBayutListing.model_validate(raw)
            raw_dict = dict(raw)
        else:
            source = raw
            raw_dict = source.model_dump()

        detail_data = detail or {}

        # --------------------------------------------------------------
        # Build a unified text source for deterministic rules.
        # --------------------------------------------------------------

        rules_input = self._build_rules_input(
            raw_dict,
            detail_data,
        )

        rules = self.rules_parser.parse(
            rules_input
        )

        # --------------------------------------------------------------
        # Identity
        # --------------------------------------------------------------

        listing_id = self._resolve_listing_id(
            source,
            detail_data,
        )

        url = self._resolve_url(
            source,
            detail_data,
        )

        # --------------------------------------------------------------
        # Group A
        # --------------------------------------------------------------

        purpose = self._resolve_purpose(
            source,
            detail_data,
        )

        property_type = self._resolve_property_type(
            source,
            detail_data,
        )

        price = self._resolve_float(
            detail_data.get("price"),
            source.price,
        )

        area_sqm = self._resolve_float(
            detail_data.get("area_sqm"),
            source.area,
        )

        bedrooms = self._resolve_int(
            detail_data.get("bedrooms"),
            source.rooms,
        )

        bathrooms = self._resolve_int(
            detail_data.get("bathrooms"),
            source.baths,
        )

        price_period = self._normalize_price_period(
            purpose=purpose,
            rent_frequency=source.rentFrequency,
        )

        location_raw = self._resolve_location_raw(
            source,
            detail_data,
        )

        governorate, city, district = (
            self._resolve_location_hierarchy(
                source,
                detail_data,
            )
        )

        agency_name = self._extract_agency_name(
            source.agency
        )

        description_raw = self._resolve_description(
            detail_data,
            source,
        )

        language = self._detect_language(
            description_raw
        )

        amenities = self._extract_amenities(
            source
        )

        date_listed = self._timestamp_to_date(
            self._extract_created_timestamp(
                raw_dict
            )
        )

        # --------------------------------------------------------------
        # Group B — structured evidence
        # --------------------------------------------------------------

        compound_name = (
            self._extract_compound_name(source)
            or rules.get("compound_name")
        )

        developer_name = (
            self._extract_developer_name(source)
            or rules.get("developer_name")
        )

        if not compound_name or not developer_name:
            from src.ner_booster import ner_booster
            ner_text = f"{raw_dict.get('title', '')} {description_raw or ''}".strip()
            ner_res = ner_booster.extract_entities(ner_text)
            if not compound_name and ner_res.get("compound_name"):
                compound_name = ner_res["compound_name"]
            if not developer_name and ner_res.get("developer_name"):
                developer_name = ner_res["developer_name"]

        structured_finishing = (
            self._extract_finishing_level(source)
        )

        structured_delivery = (
            self._extract_delivery_status(
                source,
                detail_data,
            )
        )

        sale_type = (
            self._extract_sale_type(source)
            or rules.get("sale_type")
        )

        (
            structured_payment_type,
            down_payment_amount,
            down_payment_pct,
            installment_years,
            installment_amount,
            installment_frequency,
            cash_discount_pct,
        ) = self._extract_payment_information(
            source
        )

        # Merge amenities from structured source + text extraction
        extracted_amenities = rules.get("amenities") or []
        for am in extracted_amenities:
            if am not in amenities:
                amenities.append(am)

        # --------------------------------------------------------------
        # Group B — Deterministic Rules + Consistency Validation
        # --------------------------------------------------------------
        from src.validators import consistency_validator

        source_text = f"{raw_dict.get('title', '')} {description_raw or ''}".strip()

        # Finishing level
        finishing_level = structured_finishing or rules.get("finishing_level")

        # Delivery status & date
        delivery_status = structured_delivery or rules.get("delivery_status")
        delivery_date = rules.get("delivery_date")

        # Sale type
        if not sale_type and rules.get("sale_type"):
            sale_type = rules.get("sale_type")

        # Payment type
        payment_type = structured_payment_type or rules.get("payment_type")

        if down_payment_amount is None:
            down_payment_amount = rules.get("down_payment_amount")

        if down_payment_pct is None:
            down_payment_pct = rules.get("down_payment_pct")

        if installment_years is None:
            installment_years = rules.get("installment_years")

        if installment_amount is None:
            installment_amount = rules.get("installment_amount")

        if installment_frequency is None:
            installment_frequency = rules.get("installment_frequency")

        if cash_discount_pct is None:
            cash_discount_pct = rules.get("cash_discount_pct")

        floor_number = rules.get("floor_number")
        garden_area_sqm = rules.get("garden_area_sqm")
        roof_area_sqm = rules.get("roof_area_sqm")
        is_negotiable = rules.get("is_negotiable")

        # --------------------------------------------------------------
        # Tier 4: Cross-Field Business Consistency Validation
        # --------------------------------------------------------------
        pre_validated = {
            "price": price,
            "payment_type": payment_type,
            "down_payment_amount": down_payment_amount,
            "down_payment_pct": down_payment_pct,
            "installment_years": installment_years,
            "delivery_status": delivery_status,
            "delivery_date": delivery_date,
            "cash_discount_pct": cash_discount_pct,
        }
        reconciled, _ = consistency_validator.validate_and_reconcile(pre_validated)

        payment_type = reconciled.get("payment_type")
        down_payment_amount = reconciled.get("down_payment_amount")
        down_payment_pct = reconciled.get("down_payment_pct")
        installment_years = reconciled.get("installment_years")
        delivery_status = reconciled.get("delivery_status")
        delivery_date = reconciled.get("delivery_date")
        cash_discount_pct = reconciled.get("cash_discount_pct")

        # --------------------------------------------------------------
        # Derived fields
        # --------------------------------------------------------------

        price_per_sqm = (
            self._calculate_price_per_sqm(
                price=price,
                area_sqm=area_sqm,
            )
        )

        total_installment_cost = (
            self._calculate_total_installment_cost(
                down_payment_amount=down_payment_amount,
                installment_amount=installment_amount,
                installment_frequency=installment_frequency,
                installment_years=installment_years,
            )
        )

        return HousingListing(
            # ----------------------------------------------------------
            # Identity
            # ----------------------------------------------------------

            listing_id=listing_id,
            url=url,

            # ----------------------------------------------------------
            # Data Provenance
            # ----------------------------------------------------------

            source_discovery="algolia",
            detail_html_captured=bool(detail_data and bool(detail_data.get("description_raw") or detail_data.get("title"))),
            description_source="detail_html" if (detail_data and bool(detail_data.get("description_raw"))) else None,

            # ----------------------------------------------------------
            # Group A
            # ----------------------------------------------------------

            purpose=purpose,
            property_type=property_type,

            price=price,
            price_period=price_period,
            currency="EGP",

            bedrooms=bedrooms,
            bathrooms=bathrooms,
            area_sqm=area_sqm,

            location_raw=location_raw,
            agency_name=agency_name,
            is_verified=source.isVerified,

            date_listed=date_listed,

            description_raw=description_raw,
            language=language,

            # ----------------------------------------------------------
            # Group B
            # ----------------------------------------------------------

            compound_name=compound_name,
            developer_name=developer_name,

            governorate=governorate,
            city=city,
            district=district,

            finishing_level=finishing_level,

            delivery_status=delivery_status,
            delivery_date=rules.get(
                "delivery_date"
            ),

            sale_type=sale_type,

            payment_type=payment_type,

            down_payment_amount=down_payment_amount,
            down_payment_pct=down_payment_pct,

            installment_years=installment_years,
            installment_amount=installment_amount,
            installment_frequency=installment_frequency,

            cash_discount_pct=cash_discount_pct,

            amenities=amenities,

            floor_number=floor_number,
            garden_area_sqm=garden_area_sqm,
            roof_area_sqm=roof_area_sqm,

            is_negotiable=is_negotiable,

            # ----------------------------------------------------------
            # Derived
            # ----------------------------------------------------------

            price_per_sqm=price_per_sqm,
            total_installment_cost=total_installment_cost,
        )

    # ==================================================================
    # Rules input
    # ==================================================================

    @staticmethod
    def _build_rules_input(
        raw: dict[str, Any],
        detail: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Combine all textual evidence into one dictionary for rules.py.

        The original description is preserved separately in
        description_raw; this combined representation is only for
        extraction.
        """
        combined = dict(raw)

        detail_title = detail.get("title")

        if detail_title:
            combined["detail_title"] = detail_title

        description = detail.get(
            "description_raw"
        )

        if description:
            combined["description_raw"] = description

        canonical_url = detail.get(
            "canonical_url"
        )

        if canonical_url:
            combined["canonical_url"] = canonical_url

        # Pass through page-level fields that may be useful to rules.
        for key in (
            "purpose",
            "property_type",
            "completion_status",
            "price",
            "area_sqm",
            "bedrooms",
            "bathrooms",
            "governorate",
            "city",
            "district",
        ):
            if detail.get(key) is not None:
                combined[
                    f"detail_{key}"
                ] = detail[key]

        return combined

    # ==================================================================
    # Identity / URL
    # ==================================================================

    @staticmethod
    def _resolve_listing_id(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str:
        """
        Prefer the detail-page listing ID when available because it is the
        public Bayut property identifier.

        Algolia objectID remains the fallback stable identifier.
        """
        detail_id = detail.get("listing_id")

        if detail_id is not None:
            return str(detail_id)

        if source.objectID:
            return str(source.objectID)

        if source.id is not None:
            return str(source.id)

        if source.externalID:
            return str(source.externalID)

        raise ValueError(
            "Raw Bayut listing has no usable listing ID."
        )

    @staticmethod
    def _resolve_url(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str:
        """
        Prefer the canonical URL extracted from the actual detail page.
        """
        canonical_url = detail.get(
            "canonical_url"
        )

        if isinstance(
            canonical_url,
            str,
        ) and canonical_url.strip():
            return canonical_url.strip()

        external_id = (
            source.externalID
            or source.objectID
            or str(source.id)
        )

        return (
            "https://www.bayut.eg/"
            f"تفاصيل-{external_id}/"
            "العقار.html"
        )

    # ==================================================================
    # Group A resolution
    # ==================================================================

    @staticmethod
    def _resolve_purpose(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str | None:
        """
        Normalize both Algolia and detail-page purpose values.

        Bayut detail pages may use:
            Buy
            Rent

        Algolia uses:
            for-sale
            for-rent
        """
        values = (
            detail.get("purpose"),
            source.purpose,
        )

        for value in values:
            normalized = (
                BayutParser._normalize_purpose(
                    value
                )
            )

            if normalized is not None:
                return normalized

        return None

    @staticmethod
    def _normalize_purpose(
        purpose: Any,
    ) -> str | None:
        if not isinstance(
            purpose,
            str,
        ):
            return None

        normalized = purpose.strip().lower()

        if normalized in {
            "for-sale",
            "sale",
            "for sale",
            "buy",
            "purchase",
        }:
            return "sale"

        if normalized in {
            "for-rent",
            "rent",
            "for rent",
            "lease",
        }:
            return "rent"

        return None

    @staticmethod
    def _resolve_property_type(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str | None:
        """
        Prefer the detail-page property type when available, then fall
        back to the Algolia category hierarchy.
        """
        detail_type = detail.get(
            "property_type"
        )

        mapped_detail = (
            BayutParser._normalize_property_type(
                detail_type
            )
        )

        if mapped_detail:
            return mapped_detail

        return BayutParser._extract_property_type(
            source.category
        )

    @staticmethod
    def _normalize_property_type(
        value: Any,
    ) -> str | None:
        if not isinstance(
            value,
            str,
        ):
            return None

        normalized = normalize_text(
            value
        )

        if normalized is None:
            return None

        mapping = {
            "apartment": "apartment",
            "apartments": "apartment",
            "شقة": "apartment",
            "شقق": "apartment",

            "villa": "villa",
            "villas": "villa",
            "فيلا": "villa",
            "فلل": "villa",

            "chalet": "chalet",
            "chalets": "chalet",
            "شاليه": "chalet",
            "شاليهات": "chalet",

            "townhouse": "townhouse",
            "تاون هاوس": "townhouse",

            "duplex": "duplex",
            "دوبلكس": "duplex",

            "penthouse": "penthouse",
            "بنتهاوس": "penthouse",

            "studio": "studio",
            "ستوديو": "studio",

            "land": "land",
            "أرض": "land",
            "ارض": "land",
        }

        return mapping.get(
            normalized.strip().lower()
        )

    @staticmethod
    def _extract_property_type(
        category: list[dict[str, Any]],
    ) -> str | None:
        if not category:
            return None

        categories = sorted(
            category,
            key=lambda item: item.get(
                "level",
                0,
            ),
        )

        for item in reversed(categories):
            name = (
                item.get("nameSingular_l1")
                or item.get("nameSingular")
                or item.get("name_l1")
                or item.get("name")
            )

            normalized = (
                BayutParser._normalize_property_type(
                    name
                )
            )

            if normalized:
                return normalized

        return "other"

    @staticmethod
    def _resolve_float(
        detail_value: Any,
        algolia_value: Any,
    ) -> float | None:
        detail_number = (
            BayutParser._to_float(
                detail_value
            )
        )

        if detail_number is not None:
            return detail_number

        return BayutParser._to_float(
            algolia_value
        )

    @staticmethod
    def _resolve_int(
        detail_value: Any,
        algolia_value: Any,
    ) -> int | None:
        detail_number = (
            BayutParser._to_int(
                detail_value
            )
        )

        if detail_number is not None:
            return detail_number

        return BayutParser._to_int(
            algolia_value
        )

    @staticmethod
    def _normalize_price_period(
        *,
        purpose: str | None,
        rent_frequency: str | None,
    ) -> str | None:
        if purpose != "rent":
            return None

        if not rent_frequency:
            return None

        normalized = rent_frequency.strip().lower()

        if normalized in {
            "monthly",
            "month",
        }:
            return "monthly"

        if normalized in {
            "yearly",
            "annual",
            "year",
        }:
            return "yearly"

        return None

    # ==================================================================
    # Location
    # ==================================================================

    @staticmethod
    def _resolve_location_raw(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str | None:
        """
        Prefer the structured Algolia hierarchy because its levels are
        explicitly typed, while using detail data as a fallback.
        """
        algolia_location = (
            BayutParser._extract_location_raw(
                source.location
            )
        )

        if algolia_location:
            return algolia_location

        parts = []

        for key in (
            "governorate",
            "city",
            "district",
        ):
            value = detail.get(key)

            if isinstance(
                value,
                str,
            ) and value.strip():
                parts.append(
                    value.strip()
                )

        if not parts:
            return None

        return ", ".join(parts)

    @staticmethod
    def _resolve_location_hierarchy(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> tuple[str | None, str | None, str | None]:
        """
        Prefer Algolia's typed location hierarchy.

        Detail-page values are fallbacks.
        """
        governorate, city, district = (
            BayutParser._extract_location_hierarchy(
                source.location
            )
        )

        if governorate is None:
            governorate = BayutParser._clean_location(
                detail.get("governorate")
            )

        if city is None:
            city = BayutParser._clean_location(
                detail.get("city")
            )

        if district is None:
            district = BayutParser._clean_location(
                detail.get("district")
            )

        return governorate, city, district

    @staticmethod
    def _extract_location_raw(
        location: list[dict[str, Any]],
    ) -> str | None:
        if not location:
            return None

        names: list[str] = []

        ordered = sorted(
            location,
            key=lambda item: item.get(
                "level",
                0,
            ),
        )

        for item in ordered:
            name = (
                item.get("name_l1")
                or item.get("name")
            )

            if not isinstance(
                name,
                str,
            ):
                continue

            cleaned = name.strip()

            if cleaned:
                names.append(cleaned)

        return (
            ", ".join(names)
            if names
            else None
        )

    @staticmethod
    def _extract_location_hierarchy(
        location: list[dict[str, Any]],
    ) -> tuple[str | None, str | None, str | None]:
        if not location:
            return None, None, None

        ordered = sorted(
            location,
            key=lambda item: item.get(
                "level",
                0,
            ),
        )

        governorate = None
        city = None
        district = None

        for item in ordered:
            level = item.get(
                "level"
            )

            name = (
                item.get("name_l1")
                or item.get("name")
            )

            if not isinstance(
                name,
                str,
            ):
                continue

            name = name.strip()

            if not name:
                continue

            if level == 1:
                governorate = name

            elif level == 2:
                city = name

            elif (
                isinstance(level, int)
                and level >= 3
                and district is None
            ):
                district = name

        return (
            governorate,
            city,
            district,
        )

    @staticmethod
    def _clean_location(
        value: Any,
    ) -> str | None:
        if not isinstance(
            value,
            str,
        ):
            return None

        parts = [
            part.strip()
            for part in value.split(";")
            if part.strip()
        ]

        if not parts:
            return None

        # Preserve order while removing duplicates.
        return " / ".join(
            dict.fromkeys(parts)
        )

    # ==================================================================
    # Agency
    # ==================================================================

    @staticmethod
    def _extract_agency_name(
        agency: dict[str, Any] | None,
    ) -> str | None:
        if not agency:
            return None

        name = (
            agency.get("name_l1")
            or agency.get("name")
        )

        if not isinstance(
            name,
            str,
        ):
            return None

        return name.strip() or None

    # ==================================================================
    # Description / language
    # ==================================================================

    @staticmethod
    def _resolve_description(
        detail: dict[str, Any],
        source: RawBayutListing,
    ) -> str | None:
        """
        Detail-page description is authoritative.

        Algolia description is a fallback only.
        """
        detail_description = detail.get(
            "description_raw"
        )

        if (
            isinstance(
                detail_description,
                str,
            )
            and detail_description.strip()
        ):
            return detail_description

        for value in (
            source.description_l1,
            source.description,
        ):
            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value

        return None

    @staticmethod
    def _detect_language(
        text: str | None,
    ) -> str | None:
        if not text:
            return None

        has_arabic = any(
            "\u0600" <= char <= "\u06ff"
            for char in text
        )

        has_latin = any(
            "a" <= char.lower() <= "z"
            for char in text
        )

        if has_arabic and has_latin:
            return "mixed"

        if has_arabic:
            return "ar"

        if has_latin:
            return "en"

        return None

    # ==================================================================
    # Structured Group B
    # ==================================================================

    @staticmethod
    def _extract_compound_name(
        source: RawBayutListing,
    ) -> str | None:
        if not source.project:
            return None

        for key in (
            "name_l1",
            "name",
            "title_l1",
            "title",
        ):
            value = source.project.get(
                key
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value.strip()

        return None

    @staticmethod
    def _extract_developer_name(
        source: RawBayutListing,
    ) -> str | None:
        if not source.project:
            return None

        for key in (
            "developer",
            "developerName",
            "developer_name",
        ):
            value = source.project.get(
                key
            )

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value.strip()

            if isinstance(
                value,
                dict,
            ):
                for nested_key in (
                    "name",
                    "name_l1",
                ):
                    nested_value = value.get(
                        nested_key
                    )

                    if (
                        isinstance(
                            nested_value,
                            str,
                        )
                        and nested_value.strip()
                    ):
                        return nested_value.strip()

        return None

    @staticmethod
    def _extract_finishing_level(
        source: RawBayutListing,
    ) -> str | None:
        if not source.furnishingStatus:
            return None

        normalized = normalize_text(
            source.furnishingStatus
        )

        if normalized is None:
            return None

        if normalized.strip().lower() in {
            "furnished",
            "fully furnished",
            "مفروش",
            "مفروشة",
        }:
            return "furnished"

        return None

    @staticmethod
    def _extract_delivery_status(
        source: RawBayutListing,
        detail: dict[str, Any],
    ) -> str | None:
        """
        Prefer completion status from the detail page when available,
        then fall back to Algolia.
        """
        values = (
            detail.get("completion_status"),
            source.completionStatus,
        )

        for value in values:
            if not isinstance(
                value,
                str,
            ):
                continue

            normalized = normalize_text(
                value
            )

            if normalized is None:
                continue

            lowered = normalized.lower()

            if lowered in {
                "completed",
                "complete",
                "ready",
                "ready to move",
                "تم التسليم",
                "جاهز",
            }:
                return "ready"

            if lowered in {
                "off-plan",
                "off plan",
                "under construction",
                "تحت الإنشاء",
                "تحت الانشاء",
                "على الخارطة",
            }:
                return "off-plan"

        return None

    @staticmethod
    def _extract_sale_type(
        source: RawBayutListing,
    ) -> str | None:
        if not source.extraFields:
            return None

        ownership = source.extraFields.get(
            "ownership"
        )

        if not isinstance(
            ownership,
            str,
        ):
            return None

        normalized = ownership.strip().lower()

        if normalized == "primary":
            return "primary"

        if normalized == "resale":
            return "resale"

        return None

    # ==================================================================
    # Payment information
    # ==================================================================

    def _extract_payment_information(
        self,
        source: RawBayutListing,
    ) -> tuple[
        str | None,
        float | None,
        float | None,
        float | None,
        float | None,
        str | None,
        float | None,
    ]:
        plans = self._collect_payment_plans(
            source
        )

        down_payment_amount = self._to_float(
            source.downPayment
        )

        down_payment_pct = None
        installment_years = None
        installment_amount = None
        installment_frequency = None
        cash_discount_pct = None

        if isinstance(
            source.downPayment,
            dict,
        ):
            down_payment_amount = (
                self._first_float(
                    source.downPayment,
                    (
                        "amount",
                        "value",
                        "downPayment",
                    ),
                )
            )

            down_payment_pct = (
                self._first_float(
                    source.downPayment,
                    (
                        "percentage",
                        "percent",
                        "pct",
                    ),
                )
            )

        for plan in plans:
            if down_payment_amount is None:
                down_payment_amount = (
                    self._first_float(
                        plan,
                        (
                            "downPaymentAmount",
                            "down_payment_amount",
                            "downPayment",
                        ),
                    )
                )

            if down_payment_pct is None:
                down_payment_pct = (
                    self._first_float(
                        plan,
                        (
                            "downPaymentPercentage",
                            "downPaymentPercent",
                            "downPaymentPct",
                            "down_payment_pct",
                        ),
                    )
                )

            if installment_years is None:
                installment_years = (
                    self._first_float(
                        plan,
                        (
                            "installmentYears",
                            "installment_years",
                            "years",
                            "durationYears",
                        ),
                    )
                )

            if installment_amount is None:
                installment_amount = (
                    self._first_float(
                        plan,
                        (
                            "installmentAmount",
                            "installment_amount",
                            "amount",
                        ),
                    )
                )

            if installment_frequency is None:
                installment_frequency = (
                    self._normalize_installment_frequency(
                        self._first_string(
                            plan,
                            (
                                "installmentFrequency",
                                "installment_frequency",
                                "frequency",
                            ),
                        )
                    )
                )

            if cash_discount_pct is None:
                cash_discount_pct = (
                    self._first_float(
                        plan,
                        (
                            "cashDiscountPct",
                            "cashDiscountPercentage",
                            "cash_discount_pct",
                            "discountPercentage",
                        ),
                    )
                )

        payment_type = (
            self._determine_payment_type(
                plans=plans,
                down_payment_amount=down_payment_amount,
                down_payment_pct=down_payment_pct,
                installment_years=installment_years,
                installment_amount=installment_amount,
                installment_frequency=installment_frequency,
            )
        )

        return (
            payment_type,
            down_payment_amount,
            down_payment_pct,
            installment_years,
            installment_amount,
            installment_frequency,
            cash_discount_pct,
        )

    @staticmethod
    def _collect_payment_plans(
        source: RawBayutListing,
    ) -> list[dict[str, Any]]:
        plans: list[dict[str, Any]] = []

        for collection in (
            source.paymentPlans,
            source.paymentPlanSummaries,
        ):
            for item in collection:
                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                if item not in plans:
                    plans.append(item)

        return plans

    @staticmethod
    def _determine_payment_type(
        *,
        plans: list[dict[str, Any]],
        down_payment_amount: float | None,
        down_payment_pct: float | None,
        installment_years: float | None,
        installment_amount: float | None,
        installment_frequency: str | None,
    ) -> str | None:
        if plans:
            return "installments"

        if any(
            value is not None
            for value in (
                installment_years,
                installment_amount,
                installment_frequency,
                down_payment_amount,
                down_payment_pct,
            )
        ):
            return "installments"

        return None

    @staticmethod
    def _normalize_installment_frequency(
        value: str | None,
    ) -> str | None:
        if not value:
            return None

        normalized = normalize_text(
            value
        )

        if normalized is None:
            return None

        lowered = normalized.lower()

        if lowered in {
            "monthly",
            "month",
            "شهري",
            "شهريا",
        }:
            return "monthly"

        if lowered in {
            "quarterly",
            "quarter",
            "ربع سنوي",
            "ربع سنويا",
        }:
            return "quarterly"

        if lowered in {
            "annual",
            "yearly",
            "year",
            "سنوي",
            "سنويا",
        }:
            return "annual"

        return None

    # ==================================================================
    # Amenities
    # ==================================================================

    @staticmethod
    def _extract_amenities(
        source: RawBayutListing,
    ) -> list[str]:
        values: list[str] = []

        for collection in (
            source.amenities_l1,
            source.amenities,
        ):
            for item in collection:
                if not isinstance(
                    item,
                    str,
                ):
                    continue

                cleaned = item.strip()

                if (
                    cleaned
                    and cleaned not in values
                ):
                    values.append(cleaned)

        return values

    # ==================================================================
    # Date
    # ==================================================================

    @staticmethod
    def _extract_created_timestamp(
        raw: dict[str, Any],
    ) -> float | None:
        value = raw.get(
            "createdAt"
        )

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

        return None

    @staticmethod
    def _timestamp_to_date(
        timestamp: float | None,
    ) -> str | None:
        if timestamp is None:
            return None

        try:
            dt = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

            return dt.date().isoformat()

        except (
            OverflowError,
            OSError,
            ValueError,
        ):
            return None

    # ==================================================================
    # Derived fields
    # ==================================================================

    @staticmethod
    def _calculate_price_per_sqm(
        *,
        price: float | None,
        area_sqm: float | None,
    ) -> float | None:
        if price is None:
            return None

        if (
            area_sqm is None
            or area_sqm <= 0
        ):
            return None

        return price / area_sqm

    @staticmethod
    def _calculate_total_installment_cost(
        *,
        down_payment_amount: float | None,
        installment_amount: float | None,
        installment_frequency: str | None,
        installment_years: float | None,
    ) -> float | None:
        if down_payment_amount is None:
            return None

        if installment_amount is None:
            return None

        if installment_frequency is None:
            return None

        if installment_years is None:
            return None

        multiplier = {
            "monthly": 12,
            "quarterly": 4,
            "annual": 1,
        }.get(
            installment_frequency
        )

        if multiplier is None:
            return None

        if installment_years <= 0:
            return None

        return (
            down_payment_amount
            + (
                installment_amount
                * multiplier
                * installment_years
            )
        )

    # ==================================================================
    # Generic helpers
    # ==================================================================

    @staticmethod
    def _first_float(
        data: dict[str, Any],
        keys: tuple[str, ...],
    ) -> float | None:
        for key in keys:
            converted = (
                BayutParser._to_float(
                    data.get(key)
                )
            )

            if converted is not None:
                return converted

        return None

    @staticmethod
    def _first_string(
        data: dict[str, Any],
        keys: tuple[str, ...],
    ) -> str | None:
        for key in keys:
            value = data.get(key)

            if (
                isinstance(
                    value,
                    str,
                )
                and value.strip()
            ):
                return value.strip()

        return None

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value is None or isinstance(
            value,
            bool,
        ):
            return None

        try:
            return float(value)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _to_int(
        value: Any,
    ) -> int | None:
        if value is None or isinstance(
            value,
            bool,
        ):
            return None

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return None