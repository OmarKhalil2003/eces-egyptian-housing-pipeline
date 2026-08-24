from __future__ import annotations

import unittest
from src.detail_parser import BayutDetailParser
from src.models import HousingListing, RawBayutListing
from src.normalizer import normalize_arabic_digits, normalize_text, parse_arabic_amount
from src.parser import BayutParser
from src.rules import ListingRulesParser


class PipelineTestSuite(unittest.TestCase):

    def test_normalizer_arabic_digits(self):
        self.assertEqual(normalize_arabic_digits("١٥٠٠٠٠٠"), "1500000")
        self.assertEqual(normalize_arabic_digits("٠١٢٣٤٥٦٧٨٩"), "0123456789")

    def test_normalizer_arabic_monetary_expressions(self):
        self.assertEqual(parse_arabic_amount("1.5M"), 1_500_000.0)
        self.assertEqual(parse_arabic_amount("مليون ونصف"), 1_500_000.0)
        self.assertEqual(parse_arabic_amount("نصف مليون"), 500_000.0)
        self.assertEqual(parse_arabic_amount("500 ألف"), 500_000.0)

    def test_rules_compound_and_developer_extraction(self):
        parser = ListingRulesParser()
        sample_text = {
            "title": "شقة للبيع في سوديك فيليت sodic villette بالتجمع الخامس",
            "description_raw": "موقع مميز بالقرب من الجامعة الامريكية. من تطوير شركة سوديك SODIC.",
        }
        res = parser.parse(sample_text)
        self.assertEqual(res["compound_name"], "Villette")
        self.assertEqual(res["developer_name"], "SODIC")

    def test_rules_payment_extraction(self):
        parser = ListingRulesParser()
        sample_text = {
            "title": "فيلا للبيع في مارينا 8",
            "description_raw": "طريقة الاقساط: بمقدم 1,227,923 والباقي تقسيط يصل الي 12 سنه. بخصم كاش 25%",
        }
        res = parser.parse(sample_text)
        self.assertEqual(res["payment_type"], "both")
        self.assertEqual(res["down_payment_amount"], 1_227_923.0)
        self.assertEqual(res["installment_years"], 12.0)
        self.assertEqual(res["cash_discount_pct"], 25.0)

    def test_rules_down_payment_percentage(self):
        parser = ListingRulesParser()
        sample_text = {
            "title": "شاليه للبيع في الساحل الشمالي",
            "description_raw": "ادفع مقدم 10% واقساط على 7 سنوات بدون فوائد.",
        }
        res = parser.parse(sample_text)
        self.assertEqual(res["down_payment_pct"], 10.0)
        self.assertIsNone(res["down_payment_amount"])
        self.assertEqual(res["installment_years"], 7.0)

    def test_rules_finishing_and_delivery(self):
        parser = ListingRulesParser()
        sample_ready = {
            "title": "شقة استلام فوري متشطبة بالكامل سوبر لوكس",
            "description_raw": "جاهز للسكن الفوري والتسليم فوري.",
        }
        res_ready = parser.parse(sample_ready)
        self.assertEqual(res_ready["delivery_status"], "ready")
        self.assertIsNone(res_ready["delivery_date"])
        self.assertEqual(res_ready["finishing_level"], "super lux")

        sample_offplan = {
            "title": "تاون هاوس للبيع تحت الانشاء",
            "description_raw": "استلام سنة 2026 على الطوب الاحمر.",
        }
        res_offplan = parser.parse(sample_offplan)
        self.assertEqual(res_offplan["delivery_status"], "off-plan")
        self.assertEqual(res_offplan["delivery_date"], "2026")
        self.assertEqual(res_offplan["finishing_level"], "core & shell")

    def test_rules_amenities(self):
        parser = ListingRulesParser()
        sample = {
            "title": "دوبلكس مع جاردن ولاجون",
            "description_raw": "فيو على حمام سباحة ولاند سكيب وبحيرات، مع امن وحراسة 24 ساعة ومصعد وكلوب هاوس.",
        }
        res = parser.parse(sample)
        amenities = res["amenities"]
        self.assertIn("pool", amenities)
        self.assertIn("garden", amenities)
        self.assertIn("security", amenities)
        self.assertIn("elevator", amenities)
        self.assertIn("clubhouse", amenities)

    def test_parser_derived_fields(self):
        parser = BayutParser()
        raw = {
            "id": "1001",
            "externalID": "5001001",
            "purpose": "for-sale",
            "price": 5_000_000,
            "area": 200,
            "rooms": 3,
            "baths": 2,
        }
        detail = {
            "description_raw": "بمقدم 1,000,000 وقسط شهري 50,000 على 7 سنوات",
        }
        listing = parser.parse(raw, detail)
        self.assertEqual(listing.price_per_sqm, 25_000.0)
        self.assertEqual(listing.total_installment_cost, 5_200_000.0)


if __name__ == "__main__":
    unittest.main()
