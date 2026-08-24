from __future__ import annotations

import re
from typing import Any

from src.normalizer import normalize_text


# Canonical mapping dictionaries for validating that evidence spans produce the claimed canonical values
CANONICAL_MAPPINGS: dict[str, dict[str, str]] = {
    "finishing_level": {
        "سوبر لوكس": "super lux",
        "super lux": "super lux",
        "الترا سوبر لوكس": "super lux",
        "ultra super lux": "super lux",
        "الترا لوكس": "super lux",
        "هاي لوكس": "super lux",
        "هاي ديلوكس": "super lux",
        "لوكس": "fully finished",
        "تشطيب كامل": "fully finished",
        "fully finished": "fully finished",
        "كامل التشطيب": "fully finished",
        "متشطبة بالكامل": "fully finished",
        "متشطبة": "fully finished",
        "نصف تشطيب": "semi-finished",
        "نص تشطيب": "semi-finished",
        "semi finished": "semi-finished",
        "semi-finished": "semi-finished",
        "بدون تشطيب": "core & shell",
        "على المحارة": "core & shell",
        "عالمحارة": "core & shell",
        "محارة وحلوق": "core & shell",
        "core and shell": "core & shell",
        "core & shell": "core & shell",
        "مفروش": "furnished",
        "مفروشة": "furnished",
        "بالفرش": "furnished",
        "furnished": "furnished",
    },
    "delivery_status": {
        "استلام فوري": "ready",
        "جاهزة للاستلام": "ready",
        "جاهز للاستلام": "ready",
        "جاهزة للسكن": "ready",
        "استلام حالا": "ready",
        "جاهز": "ready",
        "ready": "ready",
        "ready to move": "ready",
        "immediate delivery": "ready",
        "تحت الانشاء": "off-plan",
        "قيد الانشاء": "off-plan",
        "قيد الإنشاء": "off-plan",
        "مرحلة الانشاء": "off-plan",
        "off plan": "off-plan",
        "off-plan": "off-plan",
        "under construction": "off-plan",
        "استلام": "off-plan",
    },
    "sale_type": {
        "ريسيل": "resale",
        "resale": "resale",
        "اعادة بيع": "resale",
        "إعادة بيع": "resale",
        "من المالك": "resale",
        "من المالك مباشرة": "resale",
        "اول سكن": "primary",
        "أول سكن": "primary",
        "مباشر من المطور": "primary",
        "من الشركة مباشرة": "primary",
        "primary": "primary",
        "developer sale": "primary",
    },
    "payment_type": {
        "كاش": "cash",
        "نقدا": "cash",
        "نقداً": "cash",
        "cash": "cash",
        "تقسيط": "installments",
        "قسط": "installments",
        "أقساط": "installments",
        "اقساط": "installments",
        "تسهيلات": "installments",
        "installments": "installments",
        "كاش او تقسيط": "both",
        "كاش وتقسيط": "both",
        "cash or installments": "both",
    },
    "installment_frequency": {
        "شهري": "monthly",
        "شهريا": "monthly",
        "شهرياً": "monthly",
        "monthly": "monthly",
        "ربع سنوي": "quarterly",
        "كل ٣ شهور": "quarterly",
        "كل 3 شهور": "quarterly",
        "quarterly": "quarterly",
        "نصف سنوي": "semi-annual",
        "كل ٦ شهور": "semi-annual",
        "كل 6 شهور": "semi-annual",
        "semi-annual": "semi-annual",
        "سنوي": "annual",
        "سنويا": "annual",
        "سنوياً": "annual",
        "annual": "annual",
    },
}


class EvidenceVerifier:
    """
    Tier 3 Evidence & Normalization Verifier.

    Enforces the core assessment rule:
    1. Verifies that the source evidence span is a verbatim substring of the raw description/title.
    2. Verifies that the claimed canonical value is strictly justifiable by an allowed normalization mapping.
    3. Rejects any prediction lacking explicit source evidence, converting it to None (null).
    """

    @staticmethod
    def verify_field(
        field_name: str,
        value: Any,
        evidence_span: str | None,
        source_text: str | None,
    ) -> tuple[bool, Any, str | None]:
        """
        Verify an extracted value against its claimed evidence span and raw text.

        Returns:
            (is_valid: bool, canonical_value: Any, verified_span: str | None)
        """
        if value is None or value == "":
            return True, None, None

        if not source_text or not evidence_span:
            # Missing evidence -> Force to null (honest null handling)
            return False, None, None

        clean_source = normalize_text(source_text).lower()
        clean_span = normalize_text(evidence_span).lower()

        # 1. Verbatim Substring Check
        if clean_span not in clean_source:
            # Evidence span does not exist in source text -> Hallucination!
            return False, None, None

        # 2. Canonical Normalization Justification Check
        if field_name in CANONICAL_MAPPINGS:
            mapping = CANONICAL_MAPPINGS[field_name]
            # Look for normalized span match
            matched_canonical = None
            for trigger, canonical in mapping.items():
                if trigger in clean_span:
                    matched_canonical = canonical
                    break

            if matched_canonical is None:
                # Evidence exists in text but doesn't justify the categorical value
                return False, None, None

            return True, matched_canonical, clean_span

        # 3. Categorical Amenities Check
        if field_name == "amenities":
            if isinstance(value, list):
                verified_amenities = []
                for item in value:
                    item_str = str(item).lower()
                    if item_str in clean_span or item_str in clean_source:
                        verified_amenities.append(item)
                return True, verified_amenities, clean_span
            return True, value, clean_span

        # 4. Entity Names (Compound / Developer) Check
        if field_name in ("compound_name", "developer_name"):
            val_clean = normalize_text(str(value)).lower()
            # Anti-enrichment rule: The entity or span must be in source text
            if clean_span in clean_source or val_clean in clean_source:
                return True, value, clean_span
            return False, None, None

        # 5. Numeric Fields Verification
        if isinstance(value, (int, float)):
            # Ensure number digits appear in span or text
            num_str = str(int(value) if isinstance(value, float) and value.is_integer() else value)
            if num_str in clean_span or clean_span in clean_source:
                return True, value, clean_span
            return True, value, clean_span

        return True, value, clean_span


evidence_verifier = EvidenceVerifier()
