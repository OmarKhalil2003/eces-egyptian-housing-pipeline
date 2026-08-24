from __future__ import annotations

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any


# ---------------------------------------------------------------------------
# Arabic character normalization
# ---------------------------------------------------------------------------

_ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)

_ARABIC_LETTER_REPLACEMENTS = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
    }
)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def normalize_arabic_digits(text: str) -> str:
    return text.translate(_ARABIC_DIGITS)


def normalize_arabic_letters(text: str) -> str:
    return text.translate(_ARABIC_LETTER_REPLACEMENTS)


def remove_diacritics(text: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(char)
    )


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_text(text: str | None) -> str | None:
    """
    Normalize text for internal processing.

    The original description_raw must remain untouched.
    """
    if text is None:
        return None

    text = normalize_unicode(text)
    text = normalize_arabic_digits(text)
    text = normalize_arabic_letters(text)
    text = remove_diacritics(text)
    text = normalize_whitespace(text)

    return text


# ---------------------------------------------------------------------------
# Numeric normalization
# ---------------------------------------------------------------------------

_ARABIC_NUMBER_WORDS = {
    "صفر": 0,
    "واحد": 1,
    "واحدة": 1,
    "اثنين": 2,
    "اثنان": 2,
    "اتنين": 2,
    "ثلاثة": 3,
    "تلاتة": 3,
    "اربعة": 4,
    "أربعة": 4,
    "خمسة": 5,
    "خمسه": 5,
    "ستة": 6,
    "سته": 6,
    "سبعة": 7,
    "سبعه": 7,
    "ثمانية": 8,
    "تمانية": 8,
    "تسعة": 9,
    "تسعه": 9,
}

_SCALE_WORDS = {
    "الف": 1_000,
    "الفا": 1_000,
    "ألف": 1_000,
    "آلاف": 1_000,
    "مليون": 1_000_000,
    "ملايين": 1_000_000,
    "مليار": 1_000_000_000,
}


def clean_numeric_string(value: str) -> str:
    value = normalize_text(value) or ""

    value = value.replace(",", "")
    value = value.replace("٬", "")
    value = value.replace(" ", "")

    return value


def parse_decimal(value: str) -> Decimal | None:
    cleaned = clean_numeric_string(value)

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_numeric_token(value: str) -> float | None:
    """
    Parse common numeric formats:

    150
    150.5
    1,500,000
    1.5M
    750K
    """
    if not value:
        return None

    normalized = normalize_text(value) or ""

    normalized = normalized.replace("٬", ",").strip()

    million_match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*[mM](?:illion)?",
        normalized,
    )

    if million_match:
        return float(million_match.group(1)) * 1_000_000

    thousand_match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*[kK]",
        normalized,
    )

    if thousand_match:
        return float(thousand_match.group(1)) * 1_000

    cleaned = clean_numeric_string(normalized)

    try:
        return float(Decimal(cleaned))
    except InvalidOperation:
        return None


def parse_arabic_amount(value: str) -> float | None:
    """
    Parse common Arabic monetary expressions.

    Examples:
        1.5M
        2 مليون
        مليون ونصف
        نصف مليون
        500 ألف
    """
    if not value:
        return None

    normalized = normalize_text(value)

    if normalized is None:
        return None

    # Standard numeric notation first.
    direct = parse_numeric_token(normalized)

    if direct is not None:
        return direct

    # 1.5 مليون
    match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*مليون",
        normalized,
    )

    if match:
        return float(match.group(1)) * 1_000_000.0

    # 500 ألف
    match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*(ألف|الف|آلاف)",
        normalized,
    )

    if match:
        return float(match.group(1)) * 1_000.0

    # مليون ونصف / مليون ونص / نصف مليون / ربع مليون
    cleaned_spaces = normalize_whitespace(re.sub(r"\s+", " ", normalized))
    if cleaned_spaces in {
        "مليون ونصف",
        "مليون ونص",
        "مليون و نصف",
        "مليون و نص",
    }:
        return 1_500_000.0

    if cleaned_spaces in {
        "نصف مليون",
        "نص مليون",
        "نصف و مليون",
    }:
        return 500_000.0

    if cleaned_spaces in {"ربع مليون", "ربع و مليون"}:
        return 250_000.0

    # 2 مليون ونصف
    match = re.fullmatch(
        r"([0-9]+(?:\.[0-9]+)?)\s*مليون\s*(?:و|\+)?\s*(نصف|نص)",
        cleaned_spaces,
    )

    if match:
        return (
            float(match.group(1)) + 0.5
        ) * 1_000_000.0

    return None


# ---------------------------------------------------------------------------
# Percentages
# ---------------------------------------------------------------------------

def parse_percentage(value: str) -> float | None:
    """
    Examples:

        10%
        ١٠٪
        10 percent
    """
    if not value:
        return None

    normalized = normalize_text(value)

    if normalized is None:
        return None

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(?:%|٪|percent|per\s*cent)",
        normalized,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    result = float(match.group(1))

    if not 0 <= result <= 100:
        return None

    return result


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

def parse_area_sqm(value: str) -> float | None:
    if not value:
        return None

    normalized = normalize_text(value)

    if normalized is None:
        return None

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*"
        r"(?:sqm|sq\.?\s*m|m2|m²|متر\s*مربع|متر)",
        normalized,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    return float(match.group(1))


def parse_integer(value: str) -> int | None:
    if not value:
        return None

    normalized = normalize_text(value)

    if normalized is None:
        return None

    match = re.search(r"\d+", normalized)

    if not match:
        return None

    try:
        return int(match.group())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Category normalization
# ---------------------------------------------------------------------------

def normalize_finishing_level(
    value: str | None,
) -> str | None:
    if not value:
        return None

    text = normalize_text(value)

    if text is None:
        return None

    lowered = text.lower()

    if any(
        phrase in lowered
        for phrase in (
            "fully finished",
            "تشطيب كامل",
        )
    ):
        return "fully finished"

    if any(
        phrase in lowered
        for phrase in (
            "super lux",
            "superlux",
            "سوبر لوكس",
        )
    ):
        return "super lux"

    if any(
        phrase in lowered
        for phrase in (
            "semi-finished",
            "semi finished",
            "نصف تشطيب",
            "نص تشطيب",
        )
    ):
        return "semi-finished"

    if any(
        phrase in lowered
        for phrase in (
            "core & shell",
            "core and shell",
            "core shell",
            "على الطوب",
            "بدون تشطيب",
        )
    ):
        return "core & shell"

    if any(
        phrase in lowered
        for phrase in (
            "furnished",
            "fully furnished",
            "مفروش",
            "مفروشة",
        )
    ):
        return "furnished"

    return "unknown"


def normalize_installment_frequency(
    value: str | None,
) -> str | None:
    if not value:
        return None

    text = normalize_text(value)

    if text is None:
        return None

    lowered = text.lower()

    if any(
        phrase in lowered
        for phrase in (
            "monthly",
            "per month",
            "each month",
            "شهري",
            "شهريا",
            "كل شهر",
        )
    ):
        return "monthly"

    if any(
        phrase in lowered
        for phrase in (
            "quarterly",
            "every 3 months",
            "every three months",
            "ربع سنوي",
            "ربع سنويا",
            "كل 3 شهور",
            "كل ثلاثة شهور",
        )
    ):
        return "quarterly"

    if any(
        phrase in lowered
        for phrase in (
            "annual",
            "yearly",
            "per year",
            "every year",
            "سنوي",
            "سنويا",
            "كل سنة",
            "كل عام",
        )
    ):
        return "annual"

    return None


def normalize_payment_type(
    value: str | None,
) -> str | None:
    if not value:
        return None

    text = normalize_text(value)

    if text is None:
        return None

    lowered = text.lower()

    has_cash = any(
        phrase in lowered
        for phrase in (
            "cash",
            "كاش",
            "نقدا",
            "نقدًا",
            "الدفع كاش",
        )
    )

    has_installments = any(
        phrase in lowered
        for phrase in (
            "installment",
            "installments",
            "تقسيط",
            "قسط",
            "أقساط",
            "اقساط",
        )
    )

    if has_cash and has_installments:
        return "both"

    if has_installments:
        return "installments"

    if has_cash:
        return "cash"

    return None


# ---------------------------------------------------------------------------
# Generic helper
# ---------------------------------------------------------------------------

def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)

    if isinstance(value, list):
        return [
            normalize_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: normalize_value(item)
            for key, item in value.items()
        }

    return value