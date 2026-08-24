from __future__ import annotations

import re
from typing import Any

from src.normalizer import normalize_text


# ---------------------------------------------------------------------------
# Egyptian Real Estate Gazetteers
# ---------------------------------------------------------------------------

KNOWN_COMPOUNDS: dict[str, str] = {
    # New Cairo / 5th Settlement / Mostakbal City / New Capital
    "sodic villette": "Villette",
    "villette": "Villette",
    "فيليت": "Villette",
    "سوديك فيليت": "Villette",
    "sarai": "Sarai",
    "سراي": "Sarai",
    "كمبوند سراي": "Sarai",
    "madinaty": "Madinaty",
    "مدينتي": "Madinaty",
    "مدينتى": "Madinaty",
    "rehab": "Al Rehab",
    "al rehab": "Al Rehab",
    "الرحاب": "Al Rehab",
    "mivida": "Mivida",
    "ميفيدا": "Mivida",
    "hyde park": "Hyde Park",
    "هايد بارك": "Hyde Park",
    "mountain view icity": "Mountain View iCity",
    "ماونتن فيو اي سيتي": "Mountain View iCity",
    "ماونتن فيو اى سيتى": "Mountain View iCity",
    "اي سيتي": "Mountain View iCity",
    "اى سيتى": "Mountain View iCity",
    "icity": "Mountain View iCity",
    "mountain view hyde park": "Mountain View Hyde Park",
    "ماونتن فيو هايد بارك": "Mountain View Hyde Park",
    "mountain view executive": "Mountain View Executive",
    "zed east": "Zed East",
    "زد ايست": "Zed East",
    "زد التجمع": "Zed East",
    "il bosco": "Il Bosco",
    "البوسكو": "Il Bosco",
    "il bosco city": "Il Bosco City",
    "البوسكو سيتي": "Il Bosco City",
    "البوسكو سيتى": "Il Bosco City",
    "celia": "Celia",
    "سيليا": "Celia",
    "al burouj": "Al Burouj",
    "البروج": "Al Burouj",
    "swan lake": "Swan Lake",
    "سوان ليك": "Swan Lake",
    "waterway": "The Waterway",
    "the waterway": "The Waterway",
    "واتر واي": "The Waterway",
    "ووتر واي": "The Waterway",
    "district 5": "District 5",
    "ديستركت 5": "District 5",
    "دستركت 5": "District 5",
    "jade park": "Jade Park",
    "جيد بارك": "Jade Park",
    "جايد بارك": "Jade Park",
    "jayd": "Jade Park",
    "جايد": "Jade Park",
    "galleria moon valley": "Galleria Moon Valley",
    "جاليريا مون فالي": "Galleria Moon Valley",
    "جاليريا": "Galleria Moon Valley",
    "stone residence": "Stone Residence",
    "ستون ريزيدنس": "Stone Residence",
    "stone park": "Stone Park",
    "ستون بارك": "Stone Park",
    "eastown": "Eastown",
    "ايست تاون": "Eastown",
    "katameya dunes": "Katameya Dunes",
    "قطامية ديونز": "Katameya Dunes",
    "katameya heights": "Katameya Heights",
    "قطامية هايتس": "Katameya Heights",
    "katameya palms": "Katameya Palms",
    "قطامية بالمز": "Katameya Palms",
    "fifth square": "Fifth Square",
    "فيفث سكوير": "Fifth Square",
    "trio gardens": "Trio Gardens",
    "تريو جاردنز": "Trio Gardens",
    "azad": "Azad",
    "ازاد": "Azad",
    "lake view": "Lake View",
    "ليك فيو": "Lake View",
    "bloomfields": "Bloomfields",
    "بلوم فيلدز": "Bloomfields",
    "midtown sky": "Midtown Sky",
    "ميدتاون سكاي": "Midtown Sky",
    "midtown condo": "Midtown Condo",
    "ميدتاون كوندو": "Midtown Condo",
    "midtown solo": "Midtown Solo",
    "ميدتاون سولو": "Midtown Solo",
    "de joya": "De Joya",
    "دي جويا": "De Joya",
    "rivan": "Rivan",
    "ريفان": "Rivan",
    "scene 7": "Scene 7",
    "سين 7": "Scene 7",
    "castle landmark": "Castle Landmark",
    "كاسل لاند مارك": "Castle Landmark",
    "palm hills new cairo": "Palm Hills New Cairo",
    "بالم هيلز التجمع": "Palm Hills New Cairo",
    "بالم هيلز نيو كايرو": "Palm Hills New Cairo",

    # Sheikh Zayed / 6th of October / Giza
    "badya": "Badya",
    "بادية": "Badya",
    "باديه": "Badya",
    "palm hills": "Palm Hills",
    "بالم هيلز": "Palm Hills",
    "palm parks": "Palm Parks",
    "بالم باركس": "Palm Parks",
    "palm valley": "Palm Valley",
    "بالم فالي": "Palm Valley",
    "beverly hills": "Beverly Hills",
    "بيفرلي هيلز": "Beverly Hills",
    "بيفرلى هيلز": "Beverly Hills",
    "zayed dunes": "Zayed Dunes",
    "زايد ديونز": "Zayed Dunes",
    "allegria": "Allegria",
    "اليجريا": "Allegria",
    "new giza": "New Giza",
    "نيو جيزة": "New Giza",
    "نيو جيزه": "New Giza",
    "chillout park": "Mountain View Chillout Park",
    "تشيل اوت بارك": "Mountain View Chillout Park",
    "mountain view october park": "Mountain View October Park",
    "ماونتن فيو اكتوبر بارك": "Mountain View October Park",
    "o west": "O West",
    "او ويست": "O West",
    "zed towers": "Zed Towers",
    "زد الشيخ زايد": "Zed Towers",
    "ابراج زد": "Zed Towers",
    "sun capital": "Sun Capital",
    "صن كابيتال": "Sun Capital",
    "pyramids hills": "Pyramids Hills",
    "بيراميدز هيلز": "Pyramids Hills",
    "dreamland": "Dreamland",
    "دريم لاند": "Dreamland",
    "westown": "Westown",
    "ويست تاون": "Westown",
    "keeva": "Keeva",
    "كيفا": "Keeva",
    "aeon": "Aeon",
    "ايون": "Aeon",
    "grand heights": "Grand Heights",
    "جراند هايتس": "Grand Heights",

    # Coastal / Alexandria / Red Sea
    "marassi": "Marassi",
    "مراسي": "Marassi",
    "مراسى": "Marassi",
    "hacienda bay": "Hacienda Bay",
    "هاسيندا باي": "Hacienda Bay",
    "hacienda white": "Hacienda White",
    "هاسيندا وايت": "Hacienda White",
    "hacienda red": "Hacienda Red",
    "fouka bay": "Fouka Bay",
    "فوكا باي": "Fouka Bay",
    "cali coast": "Cali Coast",
    "كالي كوست": "Cali Coast",
    "silver sands": "Silver Sands",
    "سيلفر ساندز": "Silver Sands",
    "mountain view ras el hikma": "Mountain View Ras El Hikma",
    "ماونتن فيو راس الحكمة": "Mountain View Ras El Hikma",
    "il monte galala": "IL Monte Galala",
    "المونت جلالة": "IL Monte Galala",
    "المونت جلاله": "IL Monte Galala",
    "el gouna": "El Gouna",
    "الجونة": "El Gouna",
    "الجونه": "El Gouna",
    "somabay": "Somabay",
    "سوما باي": "Somabay",
    "makadi heights": "Makadi Heights",
    "مكادي هايتس": "Makadi Heights",
    "marina 8": "Marina 8",
    "مارينا 8": "Marina 8",
    "marina": "Marina",
    "مارينا": "Marina",
    "telal": "Telal",
    "تلال": "Telal",
    "amwaj": "Amwaj",
    "امواج": "Amwaj",
    "gaia": "Gaia",
    "جايا": "Gaia",
    "alex west": "Alex West",
    "اليكس ويست": "Alex West",
    "palm hills alexandria": "Palm Hills Alexandria",
    "بالم هيلز اسكندرية": "Palm Hills Alexandria",
    "بالم هيلز الاسكندرية": "Palm Hills Alexandria",
    "shati al nakhil": "Shati Al Nakhil",
    "شاطئ النخيل": "Shati Al Nakhil",
    "شاطي النخيل": "Shati Al Nakhil",
}

KNOWN_DEVELOPERS: dict[str, str] = {
    "emaar": "Emaar Misr",
    "emaar misr": "Emaar Misr",
    "اعمار": "Emaar Misr",
    "إعمار": "Emaar Misr",
    "اعمار مصر": "Emaar Misr",
    "sodic": "SODIC",
    "سوديك": "SODIC",
    "palm hills": "Palm Hills Developments",
    "palm hills developments": "Palm Hills Developments",
    "بالم هيلز": "Palm Hills Developments",
    "بالم هيلز للتطوير": "Palm Hills Developments",
    "tmg": "Talaat Moustafa Group (TMG)",
    "talaat moustafa": "Talaat Moustafa Group (TMG)",
    "طلعت مصطفى": "Talaat Moustafa Group (TMG)",
    "مجموعة طلعت مصطفى": "Talaat Moustafa Group (TMG)",
    "mountain view": "Mountain View (DMG)",
    "dmg": "Mountain View (DMG)",
    "ماونتن فيو": "Mountain View (DMG)",
    "دار المعمار": "Mountain View (DMG)",
    "ora": "Ora Developers",
    "ora developers": "Ora Developers",
    "اورا": "Ora Developers",
    "أورا": "Ora Developers",
    "اورا ديفلوبرز": "Ora Developers",
    "نجيب ساويرس": "Ora Developers",
    "misr italia": "Misr Italia Properties",
    "مصر ايطاليا": "Misr Italia Properties",
    "مصر إيطاليا": "Misr Italia Properties",
    "tatweer misr": "Tatweer Misr",
    "تطوير مصر": "Tatweer Misr",
    "hassan allam": "Hassan Allam Properties",
    "حسن علام": "Hassan Allam Properties",
    "city edge": "City Edge Developments",
    "سيتي ايدج": "City Edge Developments",
    "سيتي إيدج": "City Edge Developments",
    "mnhd": "Madinet Masr (MNHD)",
    "madinet masr": "Madinet Masr (MNHD)",
    "مدينة مصر": "Madinet Masr (MNHD)",
    "مدينة نصر للاسكان": "Madinet Masr (MNHD)",
    "مدينة نصر للإسكان": "Madinet Masr (MNHD)",
    "al ahly sabbour": "Al Ahly Sabbour",
    "sabbour": "Al Ahly Sabbour",
    "الاهلي صبور": "Al Ahly Sabbour",
    "الأهلي صبور": "Al Ahly Sabbour",
    "صبور": "Al Ahly Sabbour",
    "inertia": "Inertia Egypt",
    "انرشيا": "Inertia Egypt",
    "اينرشيا": "Inertia Egypt",
    "hyde park developments": "Hyde Park Developments",
    "هايد بارك للتطوير": "Hyde Park Developments",
    "orascom": "Orascom Development",
    "اوراسكوم": "Orascom Development",
    "أوراسكوم": "Orascom Development",
    "la vista": "La Vista Developments",
    "لافيستا": "La Vista Developments",
    "marakez": "Marakez",
    "مراكز": "Marakez",
    "better home": "Better Home",
    "بيتر هوم": "Better Home",
    "new plan": "New Plan Developments",
    "نيو بلان": "New Plan Developments",
    "taj misr": "Taj Misr",
    "تاج مصر": "Taj Misr",
    "al marasem": "Al Marasem Development",
    "المراسم": "Al Marasem Development",
    "المراسم الدولية": "Al Marasem Development",
    "sed": "Saudi Egyptian Developers (SED)",
    "الشركة السعودية المصرية": "Saudi Egyptian Developers (SED)",
    "times developments": "Times Developments",
    "تايمز للتطوير": "Times Developments",
    "lmd": "LMD (Landmark Sabbour)",
    "landmark": "LMD (Landmark Sabbour)",
    "لاندمارك صبور": "LMD (Landmark Sabbour)",
    "akam": "Akam Developments",
    "اكام": "Akam Developments",
    "عكام": "Akam Developments",
    "living yards": "Living Yards Developments",
    "ليفينج ياردز": "Living Yards Developments",
    "gates developments": "Gates Developments",
    "جيتس للتطوير": "Gates Developments",
    "melee": "Melee Developments",
    "ميلي": "Melee Developments",
}


class ListingRulesParser:
    """
    Deterministic extraction from Bayut listing text.

    Inputs may include:
        - title
        - title_l1
        - keywords
        - keywords_l1
        - detail_title
        - description_raw

    The parser extracts only information explicitly stated in the
    supplied text. Missing information remains None.
    """

    _ARABIC_DIGITS = str.maketrans(
        "٠١٢٣٤٥٦٧٨٩",
        "0123456789",
    )

    def parse(
        self,
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        text = self._build_text(raw)

        return {
            "compound_name": self._extract_compound(text),
            "developer_name": self._extract_developer(text),
            "finishing_level": self._extract_finishing(text),
            "delivery_status": self._extract_delivery_status(text),
            "delivery_date": self._extract_delivery_date(text),
            "sale_type": self._extract_sale_type(text),
            "payment_type": self._extract_payment_type(text),
            "cash_discount_pct": self._extract_cash_discount(text),
            "down_payment_amount": self._extract_down_payment_amount(text),
            "down_payment_pct": self._extract_down_payment_pct(text),
            "installment_years": self._extract_installment_years(text),
            "installment_amount": self._extract_installment_amount(text),
            "installment_frequency": self._extract_installment_frequency(text),
            "amenities": self._extract_amenities(text),
            "floor_number": self._extract_floor_number(text),
            "garden_area_sqm": self._extract_area(
                text,
                (
                    r"(?:private\s+)?garden(?:\s+area)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:sqm|m2|m|square\s*meters?)?",
                    r"حديقة(?:\s+خاصة)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:م|متر|مترًا|أمتار|متر\s*مربع|مترًا\s*مربعًا)?",
                    r"مساحة\s+الحديقة\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:م|متر|مترًا|أمتار|متر\s*مربع)?",
                    r"جاردن(?:\s+خاصة)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:م|متر|مترًا|أمتار|sqm|m2)?",
                ),
            ),
            "roof_area_sqm": self._extract_area(
                text,
                (
                    r"(?:roof|roof\s+area)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:sqm|m2|m|square\s*meters?)?",
                    r"(?:رووف|روف|سطح)(?:\s+مساحة)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:م|متر|مترًا|أمتار|متر\s*مربع)?",
                ),
            ),
            "is_negotiable": self._extract_negotiable(text),
        }

    # ------------------------------------------------------------------
    # Text preparation
    # ------------------------------------------------------------------

    @classmethod
    def _build_text(
        cls,
        raw: dict[str, Any],
    ) -> str:
        parts: list[str] = []

        for key in (
            "title",
            "title_l1",
            "detail_title",
        ):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value)

        for key in (
            "keywords",
            "keywords_l1",
        ):
            value = raw.get(key)
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        parts.append(item)

        description = raw.get("description_raw")
        if isinstance(description, str) and description.strip():
            parts.append(description)

        text = "\n".join(parts)
        text = text.translate(cls._ARABIC_DIGITS)

        normalized = normalize_text(text)
        return normalized or ""

    # ------------------------------------------------------------------
    # Compound & Developer extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_compound(text: str) -> str | None:
        if not text:
            return None

        lowered = text.lower()

        # Sort known compounds by alias length descending so multi-word matches take precedence
        for alias, canonical in sorted(
            KNOWN_COMPOUNDS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return canonical

        # Regex fallback for compound patterns like "كمبوند [اسم]"
        match = re.search(
            r"(?:كمبوند|مشروع|قرية|منتجع|compound|project)\s+([A-Za-z\u0600-\u06ff\s]{3,25}?)(?:\s+(?:في|فى|ب|بالقرب|بجوار|امام|أمام|على|طريق|\n|,|\.|\-))",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).strip()
            # Avoid picking up generic stop words
            if len(candidate) >= 3 and not any(
                stop in candidate for stop in ("موقع", "قلب", "خدمات", "مساحة", "طريق")
            ):
                return candidate.title()

        return None

    @staticmethod
    def _extract_developer(text: str) -> str | None:
        if not text:
            return None

        lowered = text.lower()

        for alias, canonical in sorted(
            KNOWN_DEVELOPERS.items(), key=lambda x: len(x[0]), reverse=True
        ):
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                return canonical

        match = re.search(
            r"(?:شركة|مطور|developer)\s*[:\-]?\s*([A-Za-z\u0600-\u06ff\s]{3,30}?)(?:\s+(?:للتطوير|للاستثمار|العقاري|العقارية|\n|,|\.|\-))",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            candidate = match.group(1).strip()
            if len(candidate) >= 3:
                return candidate.title()

        return None

    # ------------------------------------------------------------------
    # Finishing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_finishing(text: str) -> str | None:
        if not text:
            return None

        if (
            "مفروش" in text
            or "مفروشة" in text
            or "بالفرش" in text
            or re.search(
                r"\b(?:fully\s+)?furnished\b",
                text,
                flags=re.IGNORECASE,
            )
        ):
            return "furnished"

        if re.search(
            r"\bsuper\s+(?:deluxe|lux)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "super lux"

        if any(
            phrase in text
            for phrase in (
                "سوبر لوكس",
                "سوبر لوكـس",
                "الترا سوبر لوكس",
                "ألترا سوبر لوكس",
                "الترا لوكس",
                "تشطيبات سوبر لوكس",
                "تشطيب سوبر لوكس",
                "هاي لوكس",
                "هاى لوكس",
                "هاي-لوكس",
                "تشطيب فاخر",
                "فاخر",
                "ultra super lux",
                "super deluxe",
                "super lux",
                "high end",
                "high lux",
            )
        ):
            return "super lux"

        if any(
            phrase in text
            for phrase in (
                "كاملة التشطيب",
                "كامل التشطيب",
                "تشطيب كامل",
                "متشطب بالكامل",
                "متشطبة بالكامل",
                "متشطب",
                "متشطبة",
                "تشطيب خاص بالكامل",
                "تشطيبات خاصة بالكامل",
                "fully finished",
            )
        ) or re.search(
            r"\bfully\s+finished\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "fully finished"

        if any(
            phrase in text
            for phrase in (
                "نصف تشطيب",
                "نص تشطيب",
                "semi finished",
                "semi-finished",
            )
        ) or re.search(
            r"\bsemi[-\s]?finished\b",
            text,
            flags=re.IGNORECASE,
        ):
            return "semi-finished"

        if any(
            phrase in text
            for phrase in (
                "على الطوب",
                "علي الطوب",
                "على الطوب الاحمر",
                "علي الطوب الاحمر",
                "طوب احمر",
                "طوب أحمر",
                "على المحارة",
                "علي المحارة",
                "محارة",
                "بدون تشطيب",
                "من غير تشطيب",
                "core & shell",
                "core and shell",
            )
        ):
            return "core & shell"

        return None

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_delivery_status(text: str) -> str | None:
        if not text:
            return None

        ready_patterns = (
            r"\bready\s+to\s+move\b",
            r"\bimmediate\s+delivery\b",
            r"\bimmediate\s+handover\b",
            r"\bready\b",
        )

        for pattern in ready_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "ready"

        if any(
            phrase in text
            for phrase in (
                "استلام فوري",
                "استلام فورى",
                "جاهز للسكن",
                "جاهزة للسكن",
                "استلام مباشر",
                "تسليم فوري",
                "تسليم فورى",
                "جاهز للاستلام",
                "جاهزة للاستلام",
            )
        ):
            return "ready"

        off_plan_patterns = (
            r"\boff[-\s]?plan\b",
            r"\bunder\s+construction\b",
            r"\bunder\s+development\b",
        )

        for pattern in off_plan_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return "off-plan"

        if any(
            phrase in text
            for phrase in (
                "تحت الإنشاء",
                "تحت الانشاء",
                "قيد الإنشاء",
                "قيد الانشاء",
                "مرحلة الإنشاء",
                "مرحلة الانشاء",
                "تحت التنفيذ",
                "مشروع تحت",
            )
        ):
            return "off-plan"

        # If a future delivery year is mentioned (e.g. 2026), it is off-plan
        if re.search(r"(?:استلام|تسليم|delivery|handover).{0,30}?\b(202[5-9]|203[0-9])\b", text, flags=re.IGNORECASE):
            return "off-plan"

        return None

    # ------------------------------------------------------------------
    # Delivery Date (Off-Plan only)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_delivery_date(text: str) -> str | None:
        if not text:
            return None

        quarter_patterns = (
            r"(?:delivery|deliver|handover|تسليم|استلام)\s*(?:date|in|by|خلال|في|فى|سنة|عام|:)?\s*.{0,25}?\b(202[4-9]|203[0-9])\s*(?:-|/)?\s*(Q[1-4]|q[1-4])\b",
            r"\b(Q[1-4]|q[1-4])\s*(?:-|/)?\s*(202[4-9]|203[0-9])\b",
            r"(?:الربع\s+الاول|الربع\s+الأول)\s*(?:من|سنة|عام|:)?\s*(202[4-9]|203[0-9])",
            r"(?:الربع\s+الثاني|الربع\s+الثانى)\s*(?:من|سنة|عام|:)?\s*(202[4-9]|203[0-9])",
            r"(?:الربع\s+الثالث)\s*(?:من|سنة|عام|:)?\s*(202[4-9]|203[0-9])",
            r"(?:الربع\s+الرابع)\s*(?:من|سنة|عام|:)?\s*(202[4-9]|203[0-9])",
        )

        for pattern in quarter_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                g1, g2 = match.group(1), (match.group(2) if len(match.groups()) > 1 else "")
                if "q" in g1.lower():
                    return f"{g2} {g1.upper()}"
                elif "q" in g2.lower():
                    return f"{g1} {g2.upper()}"
                elif "الاول" in match.group(0) or "الأول" in match.group(0):
                    return f"{g1} Q1"
                elif "الثاني" in match.group(0) or "الثانى" in match.group(0):
                    return f"{g1} Q2"
                elif "الثالث" in match.group(0):
                    return f"{g1} Q3"
                elif "الرابع" in match.group(0):
                    return f"{g1} Q4"

        year_patterns = (
            r"(?:delivery|deliver|handover)\s*(?:date|in|by|:)?\s*.{0,25}?\b(202[4-9]|203[0-9])\b",
            r"(?:تسليم|استلام)\s*(?:خلال|في|فى|سنة|عام|موعد|تاريخ|:)?\s*.{0,25}?\b(202[4-9]|203[0-9])\b",
        )

        for pattern in year_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    # ------------------------------------------------------------------
    # Sale Type (Primary vs Resale)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_sale_type(text: str) -> str | None:
        if not text:
            return None

        if any(
            phrase in text
            for phrase in (
                "ريسيل",
                "ري سيل",
                "إعادة بيع",
                "اعادة بيع",
                "resale",
                "re-sale",
                "من المالك مباشرة",
                "للتنازل",
                "تنازل",
                "من المالك",
            )
        ):
            return "resale"

        if any(
            phrase in text
            for phrase in (
                "من المطور",
                "من الشركة المطورة",
                "primary",
                "developer",
                "مباشرة من المطور",
                "مباشر من المطور",
                "direct from developer",
            )
        ):
            return "primary"

        return None

    # ------------------------------------------------------------------
    # Payment type
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_payment_type(text: str) -> str | None:
        if not text:
            return None

        cash = bool(
            re.search(r"\bcash\b", text, flags=re.IGNORECASE)
        ) or any(
            phrase in text
            for phrase in (
                "بكاش",
                "كاش",
                "نقداً",
                "نقدا",
                "نقدى",
                "نقدي",
                "مطلوب كاش",
                "سعر الكاش",
                "خصم كاش",
            )
        )

        installments = bool(
            re.search(r"\binstallments?\b", text, flags=re.IGNORECASE)
        ) or any(
            phrase in text
            for phrase in (
                "بالتقسيط",
                "تقسيط",
                "القسط",
                "أقساط",
                "اقساط",
                "قسط",
                "مقدم",
                "بمقدم",
                "دفعة مقدمة",
                "فترة سداد",
                "نظام سداد",
                "انظمة سداد",
            )
        )

        if cash and installments:
            return "both"

        if installments:
            return "installments"

        if cash:
            return "cash"

        return None

    # ------------------------------------------------------------------
    # Cash discount
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_cash_discount(text: str) -> float | None:
        if not text:
            return None

        patterns = (
            r"(?:cash\s+discount|discount)\s*(?:of|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
            r"(?:بخصم|خصم)\s*([0-9]+(?:\.[0-9]+)?)\s*%",
            r"خصم\s+كاش.{0,30}?([0-9]+(?:\.[0-9]+)?)\s*%",
            r"خصم.{0,20}?الكاش\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        )

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            value = float(match.group(1))
            if 0 < value <= 100:
                return value

        return None

    # ------------------------------------------------------------------
    # Down payment amount & percentage
    # ------------------------------------------------------------------

    @classmethod
    def _extract_down_payment_amount(cls, text: str) -> float | None:
        if not text:
            return None

        # Check for zero down payment
        if any(p in text for p in ("بدون مقدم", "0 مقدم", "صفر مقدم", "zero down payment", "no down payment")):
            return 0.0

        patterns = (
            r"(?:down\s*payment|downpayment)\s*(?:of|amount|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(million|mn|m|billion|bn|thousand|k)?",
            r"(?:مقدم|دفعة\s+مقدمة|ادفع\s+مقدم|بمقدم)\s*(?:دفع|بمبلغ|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(مليون|مليار|ألف|الف)?",
        )

        for pattern in patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                # Check if this occurrence is followed by a percentage symbol
                end_pos = match.end()
                following_text = text[end_pos : end_pos + 5]
                if "%" in following_text or "٪" in following_text or "%" in match.group(0) or "٪" in match.group(0):
                    continue

                raw_num = match.group(1).replace(",", "")
                unit = match.group(2) if len(match.groups()) > 1 else None

                try:
                    num_val = float(raw_num)
                except ValueError:
                    continue

                # If no unit and number is <= 100, it's almost certainly a percentage like "مقدم 10" or "مقدم 25"
                if not unit and num_val <= 100:
                    continue

                value = cls._parse_scaled_number(
                    number_text=raw_num,
                    unit=unit,
                )

                if value is not None and value > 0:
                    return value

        return None

    @staticmethod
    def _extract_down_payment_pct(text: str) -> float | None:
        if not text:
            return None

        if any(p in text for p in ("بدون مقدم", "0% مقدم", "0% down payment", "zero down payment")):
            return 0.0

        patterns = (
            r"(?:down\s*payment|downpayment).{0,30}?([0-9]+(?:\.[0-9]+)?)\s*(?:%|٪)",
            r"(?:مقدم|دفعة\s*مقدمة|بمقدم|ادفع\s*مقدم|ادفع).{0,30}?([0-9]+(?:\.[0-9]+)?)\s*(?:%|٪)",
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:%|٪).{0,30}?(?:down\s*payment|مقدم)",
        )

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            value = float(match.group(1))
            if 0 <= value <= 100:
                return value

        return None

    # ------------------------------------------------------------------
    # Installment years
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_installment_years(text: str) -> float | None:
        if not text:
            return None

        patterns = (
            r"(?:installment|payment|plan).{0,50}?([0-9]+(?:\.[0-9]+)?)\s*(?:years?|yrs?)",
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:years?|yrs?).{0,25}?(?:installment|payment|plan)",
            r"(?:تقسيط|قسط|أقساط|اقساط|سداد).{0,60}?([0-9]+(?:\.[0-9]+)?)\s*(?:سنوات|سنة|سنه|سنين|عام|أعوام|اعوام)",
            r"(?:تقسيط|قسط|أقساط|اقساط|سداد).{0,60}?(?:إلى|الي|الى|حتى|على|علي|يصل\s*إلى|يصل\s*الي|يصل\s*الى)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:سنة|سنه|سنوات|سنين|عام|أعوام|اعوام)",
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:سنة|سنه|سنوات|سنين|عام|أعوام|اعوام).{0,25}?(?:تقسيط|قسط|أقساط|سداد)",
            r"(?:على|علي|خلال|لمدة|لمده)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:سنوات|سنة|سنه|سنين|عام|اعوام)",
        )

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            value = float(match.group(1))
            if 0 < value <= 30:
                return value

        return None

    # ------------------------------------------------------------------
    # Installment amount
    # ------------------------------------------------------------------

    @classmethod
    def _extract_installment_amount(cls, text: str) -> float | None:
        if not text:
            return None

        patterns = (
            r"(?:monthly\s+installment|installment\s+amount|installment)\s*(?:of|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(thousand|k|million|m)?",
            r"(?:و?القسط|و?قسط)\s*(?:الشهري|الشهرى|الربع\s+سنوي|السنوي|:)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(ألف|الف|مليون)?",
            r"ب?قسط\s*(?:شهري|شهرى|ربع\s+سنوى|ربع\s+سنوي)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(ألف|الف|مليون)?",
        )

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            value = cls._parse_scaled_number(
                number_text=match.group(1),
                unit=match.group(2) if len(match.groups()) > 1 else None,
            )

            if value is not None and value > 0:
                return value

        return None

    # ------------------------------------------------------------------
    # Installment frequency
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_installment_frequency(text: str) -> str | None:
        if not text:
            return None

        if re.search(r"\bmonthly\b|\bper\s+month\b", text, flags=re.IGNORECASE) or any(
            phrase in text for phrase in ("شهري", "شهريا", "الشهرى", "كل شهر", "شهرياً")
        ):
            return "monthly"

        if re.search(r"\bquarterly\b|\bevery\s+3\s+months?\b", text, flags=re.IGNORECASE) or any(
            phrase in text for phrase in ("ربع سنوي", "ربع سنويا", "ربع سنوياً", "كل 3 شهور", "كل ثلاثة شهور")
        ):
            return "quarterly"

        if re.search(r"\bannually?\b|\byearly\b|\bper\s+year\b", text, flags=re.IGNORECASE) or any(
            phrase in text for phrase in ("سنوي", "سنويا", "سنوياً", "كل سنة", "كل عام")
        ):
            return "annual"

        return None

    # ------------------------------------------------------------------
    # Amenities extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_amenities(text: str) -> list[str]:
        if not text:
            return []

        amenities: list[str] = []
        lowered = text.lower()

        amenity_rules: list[tuple[str, tuple[str, ...]]] = [
            ("pool", ("pool", "swimming pool", "حمام سباحة", "حمامات سباحة", "lagoon", "لاجون", "بحيرات")),
            ("security", ("security", "أمن", "حراسة", "كاميرات مراقبة", "امن وحراسة", "حراسه")),
            ("garage", ("garage", "parking", "جراج", "باركينج", "موقف سيارات", "بايكة")),
            ("elevator", ("elevator", "lift", "أسانسير", "اسانسير", "مصعد")),
            ("garden", ("garden", "حديقة", "جاردن", "مساحات خضراء", "لاند سكيب", "landscape")),
            ("sea view", ("sea view", "beach view", "فيو بحر", "إطلالة على البحر", "اطلالة على البحر")),
            ("clubhouse", ("clubhouse", "club house", "كلوب هاوس", "نادي صحي")),
            ("gym", ("gym", "fitness", "جيم", "صالة رياضية")),
            ("balcony", ("balcony", "terrace", "بلكونة", "تراس", "شرفة")),
            ("maids room", ("maid room", "maid's room", "غرفة خادمة", "غرفة داده", "غرفة مربية")),
            ("central ac", ("central ac", "تكييف مركزي", "تكييف مركزى")),
        ]

        for canonical, triggers in amenity_rules:
            if any(trigger in lowered for trigger in triggers):
                amenities.append(canonical)

        return amenities

    # ------------------------------------------------------------------
    # Floor
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_floor_number(text: str) -> int | None:
        if not text:
            return None

        numeric_patterns = (
            r"\bfloor\s*(?:no\.?|number)?\s*([0-9]+)\b",
            r"\b([0-9]+)(?:st|nd|rd|th)\s+floor\b",
            r"الدور\s*[:\-]?\s*([0-9]+)",
            r"الطابق\s*[:\-]?\s*([0-9]+)",
            r"\bدور\s*[:\-]?\s*([0-9]+)",
        )

        for pattern in numeric_patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1))

        arabic_ordinals = {
            "الأرضي": 0,
            "الارضي": 0,
            "أرضي": 0,
            "ارضي": 0,
            "الاول": 1,
            "الأول": 1,
            "اول": 1,
            "أول": 1,
            "الثاني": 2,
            "الثالث": 3,
            "الرابع": 4,
            "الخامس": 5,
            "السادس": 6,
            "السابع": 7,
            "الثامن": 8,
            "التاسع": 9,
            "العاشر": 10,
            "الحادي عشر": 11,
            "الثاني عشر": 12,
            "الثالث عشر": 13,
            "الرابع عشر": 14,
            "الخامس عشر": 15,
            "السادس عشر": 16,
            "السابع عشر": 17,
            "الثامن عشر": 18,
            "التاسع عشر": 19,
            "العشرون": 20,
        }

        for phrase, number in arabic_ordinals.items():
            if re.search(rf"(?:الدور|الطابق|دور)\s*[:\-]?\s*{re.escape(phrase)}\b", text):
                return number

        if re.search(r"(?:الدور|الطابق|دور).{0,5}?\b(?:أرضي|ارضي)\b", text):
            return 0

        return None

    # ------------------------------------------------------------------
    # Garden / roof area
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_area(text: str, patterns: tuple[str, ...]) -> float | None:
        if not text:
            return None

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            try:
                value = float(match.group(1))
                if value > 0:
                    return value
            except (TypeError, ValueError):
                continue

        return None

    # ------------------------------------------------------------------
    # Negotiability
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_negotiable(text: str) -> bool | None:
        if not text:
            return None

        if "غير قابل للتفاوض" in text or re.search(r"\bnon[-\s]?negotiable\b|\bnot\s+negotiable\b", text, flags=re.IGNORECASE):
            return False

        if any(
            phrase in text
            for phrase in (
                "قابل للتفاوض",
                "قابل للتفاوض فيه",
                "السعر قابل للتفاوض",
                "قابل للتفاوض فيه السعر",
                "سعر قابل للتفاوض",
            )
        ) or re.search(r"\bnegotiable\b|\bprice\s+negotiable\b", text, flags=re.IGNORECASE):
            return True

        return None

    # ------------------------------------------------------------------
    # Numeric parsing helper
    # ------------------------------------------------------------------

    @classmethod
    def _parse_scaled_number(
        cls,
        *,
        number_text: str,
        unit: str | None = None,
    ) -> float | None:
        try:
            number = float(number_text.replace(",", ""))
        except (TypeError, ValueError):
            return None

        if not unit:
            return number

        normalized_unit = unit.strip().lower()

        multipliers = {
            "million": 1_000_000,
            "mn": 1_000_000,
            "m": 1_000_000,
            "مليون": 1_000_000,
            "billion": 1_000_000_000,
            "bn": 1_000_000_000,
            "مليار": 1_000_000_000,
            "thousand": 1_000,
            "k": 1_000,
            "ألف": 1_000,
            "الف": 1_000,
        }

        multiplier = multipliers.get(normalized_unit)
        if multiplier is None:
            return number

        # If the number is already >= 10,000 and multiplier is >= 1,000,000,
        # the author wrote both full number and scale word (e.g. "1,050,000 مليون").
        if number >= 10_000 and multiplier >= 1_000_000:
            return number

        return number * multiplier