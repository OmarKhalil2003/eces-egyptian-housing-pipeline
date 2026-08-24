from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class HousingListing(BaseModel):
    """
    Canonical research-grade representation of one Bayut listing.

    Missing information is represented by None rather than inferred.
    """

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    # ------------------------------------------------------------------
    # Identity / source
    # ------------------------------------------------------------------

    listing_id: str
    url: str

    # ------------------------------------------------------------------
    # Data Provenance
    # ------------------------------------------------------------------

    source_discovery: str = "algolia"
    detail_html_captured: bool = False
    description_source: str | None = None

    # ------------------------------------------------------------------
    # Group A — stated on the source
    # ------------------------------------------------------------------

    purpose: str | None = None
    property_type: str | None = None

    price: float | None = None
    price_period: str | None = None
    currency: str | None = None

    bedrooms: int | None = None
    bathrooms: int | None = None
    area_sqm: float | None = None

    location_raw: str | None = None
    agency_name: str | None = None
    is_verified: bool | None = None
    date_listed: str | None = None

    description_raw: str | None = None
    language: str | None = None

    # ------------------------------------------------------------------
    # Group B — extracted / normalized from available source evidence
    # ------------------------------------------------------------------

    compound_name: str | None = None
    developer_name: str | None = None

    governorate: str | None = None
    city: str | None = None
    district: str | None = None

    finishing_level: str | None = None

    delivery_status: str | None = None
    delivery_date: str | None = None

    sale_type: str | None = None

    payment_type: str | None = None

    down_payment_amount: float | None = None
    down_payment_pct: float | None = None

    installment_years: float | None = None
    installment_amount: float | None = None
    installment_frequency: str | None = None

    cash_discount_pct: float | None = None

    amenities: list[str] = Field(
        default_factory=list
    )

    floor_number: int | None = None
    garden_area_sqm: float | None = None
    roof_area_sqm: float | None = None

    is_negotiable: bool | None = None

    # ------------------------------------------------------------------
    # Derived fields
    # ------------------------------------------------------------------

    price_per_sqm: float | None = None
    total_installment_cost: float | None = None


class RawBayutListing(BaseModel):
    """
    Raw/subset representation of the Bayut Algolia listing.

    Extra fields are allowed because the exact Algolia payload can evolve.
    """

    model_config = ConfigDict(
        extra="allow"
    )

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    id: int | str | None = None
    objectID: str | None = None
    externalID: str | None = None
    listing_id: str | None = None

    # ------------------------------------------------------------------
    # Group A source fields
    # ------------------------------------------------------------------

    purpose: str | None = None
    price: float | None = None
    rentFrequency: str | None = None

    title: str | None = None
    title_l1: str | None = None

    location: list[dict[str, Any]] = Field(
        default_factory=list
    )

    category: list[dict[str, Any]] = Field(
        default_factory=list
    )

    rooms: int | None = None
    baths: int | None = None
    area: float | None = None

    agency: dict[str, Any] | None = None

    isVerified: bool | None = None

    createdAt: float | int | str | None = None

    # ------------------------------------------------------------------
    # Text source
    # ------------------------------------------------------------------

    description: str | None = None
    description_l1: str | None = None

    # ------------------------------------------------------------------
    # Structured Group B source fields
    # ------------------------------------------------------------------

    amenities: list[str] = Field(
        default_factory=list
    )

    amenities_l1: list[str] = Field(
        default_factory=list
    )

    keywords: list[str] = Field(
        default_factory=list
    )

    keywords_l1: list[str] = Field(
        default_factory=list
    )

    completionStatus: str | None = None

    furnishingStatus: str | None = None

    extraFields: dict[str, Any] | None = None

    paymentPlans: list[dict[str, Any]] = Field(
        default_factory=list
    )

    paymentPlanSummaries: list[dict[str, Any]] = Field(
        default_factory=list
    )

    downPayment: Any = None

    project: dict[str, Any] | None = None

    offplanDetails: dict[str, Any] | None = None

    plotArea: float | None = None

    # ------------------------------------------------------------------
    # URL-related source fields
    # ------------------------------------------------------------------

    slug: str | None = None
    slug_l1: str | None = None


# ---------------------------------------------------------------------------
# Canonical allowed values
# ---------------------------------------------------------------------------

SUPPORTED_PURPOSES = {
    "sale",
    "rent",
}

SUPPORTED_PROPERTY_TYPES = {
    "apartment",
    "villa",
    "chalet",
    "townhouse",
    "duplex",
    "penthouse",
    "studio",
    "land",
    "other",
}

SUPPORTED_FINISHING_LEVELS = {
    "core & shell",
    "semi-finished",
    "fully finished",
    "super lux",
    "furnished",
    "unknown",
}

SUPPORTED_DELIVERY_STATUSES = {
    "ready",
    "off-plan",
}

SUPPORTED_SALE_TYPES = {
    "primary",
    "resale",
}

SUPPORTED_PAYMENT_TYPES = {
    "cash",
    "installments",
    "both",
}

SUPPORTED_INSTALLMENT_FREQUENCIES = {
    "monthly",
    "quarterly",
    "annual",
}