from __future__ import annotations

import unittest

from src.evidence_verifier import EvidenceVerifier
from src.validators import ListingConsistencyValidator


class EvidenceVerifierTestSuite(unittest.TestCase):
    """Test suite for Tier 3 Evidence & Normalization Verifier and Tier 4 Consistency Validator."""

    def setUp(self) -> None:
        self.verifier = EvidenceVerifier()
        self.validator = ListingConsistencyValidator()

    def test_valid_arabic_finishing_evidence(self) -> None:
        source = "شقة رائعة للبيع في التجمع الخامس تشطيب سوبر لوكس دور ثاني"
        is_valid, canonical, span = self.verifier.verify_field(
            field_name="finishing_level",
            value="super lux",
            evidence_span="تشطيب سوبر لوكس",
            source_text=source,
        )
        self.assertTrue(is_valid)
        self.assertEqual(canonical, "super lux")

    def test_hallucinated_evidence_rejection(self) -> None:
        source = "شقة للبيع في التجمع الخامس بدون ذكر التشطيب"
        # SLM predicted super lux with fabricated evidence
        is_valid, canonical, span = self.verifier.verify_field(
            field_name="finishing_level",
            value="super lux",
            evidence_span="سوبر لوكس",
            source_text=source,
        )
        self.assertFalse(is_valid)
        self.assertIsNone(canonical)

    def test_null_evidence_rejection(self) -> None:
        source = "شقة للبيع في كمبوند فيليت"
        # SLM inferred developer SODIC from Villette without evidence
        is_valid, canonical, span = self.verifier.verify_field(
            field_name="developer_name",
            value="SODIC",
            evidence_span=None,
            source_text=source,
        )
        self.assertFalse(is_valid)
        self.assertIsNone(canonical)

    def test_valid_delivery_status_evidence(self) -> None:
        source = "فيلا مستقلة استلام فوري بمقدم 10% واقساط على 7 سنين"
        is_valid, canonical, span = self.verifier.verify_field(
            field_name="delivery_status",
            value="ready",
            evidence_span="استلام فوري",
            source_text=source,
        )
        self.assertTrue(is_valid)
        self.assertEqual(canonical, "ready")

    def test_cross_field_payment_consistency(self) -> None:
        data = {
            "payment_type": "cash",
            "installment_years": 7.0,
            "down_payment_pct": 10.0,
        }
        reconciled, warnings = self.validator.validate_and_reconcile(data)
        # Should reconcile to "both"
        self.assertEqual(reconciled["payment_type"], "both")
        self.assertTrue(len(warnings) > 0)

    def test_cross_field_ready_delivery_date_cleared(self) -> None:
        data = {
            "delivery_status": "ready",
            "delivery_date": "2027",
        }
        reconciled, warnings = self.validator.validate_and_reconcile(data)
        # Ready property should have null delivery_date
        self.assertIsNone(reconciled["delivery_date"])


if __name__ == "__main__":
    unittest.main()
