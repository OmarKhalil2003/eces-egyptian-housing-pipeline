"""
Egyptian Real Estate Named Entity & Context Recognition Booster.

Provides zero-shot extraction (via GLiNER when installed) and fast rule-based
morphological entity chunking for compound and developer entities.
"""

from __future__ import annotations

import re
from typing import Any

from src.normalizer import normalize_text


COMPOUND_PREFIXES = (
    r"(?:كمبوند|كمباوند|كومباوند|مشروع|قرية|قريه|منتجع|مدينه|مدينة|مجمع|compound|project|resort|village)\s+([A-Za-z0-9\u0600-\u06FF\s\-]{2,35}?)(?=\s+(?:في|فى|ب|بـ|التجمع|الشيخ|اكتوبر|أكتوبر|الساحل|السخنة|السخنه|بجوار|امام|أمام|علي|على|للبيع|للايجار|للإيجار|,|\.|\n|$))",
    r"(?:داخل|بداخل|في|فى)\s+(?:كمبوند|كمباوند|مشروع|قرية|قريه|منتجع)\s+([A-Za-z0-9\u0600-\u06FF\s\-]{2,35}?)(?=\s+(?:في|فى|التجمع|اكتوبر|أكتوبر|الساحل|,|\.|\n|$))",
)

DEVELOPER_PREFIXES = (
    r"(?:شركة|شركه|مطور|تطوير|بواسطة|بواسطه|من|developer|by)\s+([A-Za-z0-9\u0600-\u06FF\s\-]{2,35}?)(?=\s+(?:العقارية|للتطوير|للتنمية|العقاريه|للاستثمار|,|\.|\n|$))",
    r"(?:شركة|شركه)\s+([A-Za-z0-9\u0600-\u06FF\s\-]{2,35}?\s+(?:العقارية|العقاريه|للتطوير|للاستثمار))",
)


class RealEstateNERBooster:
    """
    Tier 1.5: Zero-Shot & Structural Entity Recognition Booster.
    """

    def __init__(self) -> None:
        self._gliner_model = None
        self._gliner_attempted = False

    def _get_gliner(self):
        if not self._gliner_attempted:
            self._gliner_attempted = True
            try:
                from gliner import GLiNER
                self._gliner_model = GLiNER.from_pretrained("NAMAA-Space/gliner_arabic-v2.1")
            except Exception:
                self._gliner_model = None
        return self._gliner_model

    def extract_entities(self, text: str | None) -> dict[str, str | None]:
        """
        Extract compound_name and developer_name from text.
        """
        if not text or len(text.strip()) < 3:
            return {"compound_name": None, "developer_name": None}

        norm = normalize_text(text)
        results: dict[str, str | None] = {"compound_name": None, "developer_name": None}

        # 1. Try GLiNER zero-shot model if available
        gliner = self._get_gliner()
        if gliner:
            try:
                entities = gliner.predict_entities(
                    text,
                    labels=["compound_name", "developer_name", "location"],
                    threshold=0.45,
                )
                for ent in entities:
                    label = ent.get("label")
                    val = ent.get("text", "").strip()
                    if label in results and not results[label] and len(val) >= 3:
                        results[label] = val
            except Exception:
                pass

        # 2. Structural prefix matching (Compound)
        if not results["compound_name"]:
            for pattern in COMPOUND_PREFIXES:
                match = re.search(pattern, norm, flags=re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if len(val) >= 3 and val not in ("القاهرة", "الجيزة", "مصر", "الساحل", "السخنة", "التجمع", "اكتوبر"):
                        results["compound_name"] = val
                        break

        # 3. Structural prefix matching (Developer)
        if not results["developer_name"]:
            for pattern in DEVELOPER_PREFIXES:
                match = re.search(pattern, norm, flags=re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if len(val) >= 3 and val not in ("عقارات", "التطوير العقاري", "للتطوير العقاري"):
                        results["developer_name"] = val
                        break

        return results


ner_booster = RealEstateNERBooster()
