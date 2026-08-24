from __future__ import annotations

from typing import Any


class ListingConsistencyValidator:
    """
    Tier 4: Cross-Field Business Logic & Semantic Consistency Validator.

    Validates inter-field logical relationships to ensure records are
    not self-contradictory.
    """

    @staticmethod
    def validate_and_reconcile(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """
        Validates cross-field consistency and resolves logical contradictions.

        Returns:
            (reconciled_data: dict, warnings: list[str])
        """
        reconciled = dict(data)
        warnings: list[str] = []

        price = reconciled.get("price")
        payment_type = reconciled.get("payment_type")
        down_payment_amount = reconciled.get("down_payment_amount")
        down_payment_pct = reconciled.get("down_payment_pct")
        installment_years = reconciled.get("installment_years")
        delivery_status = reconciled.get("delivery_status")
        delivery_date = reconciled.get("delivery_date")

        # ------------------------------------------------------------------
        # 1. Payment Type & Installment Horizon Reconciliation
        # ------------------------------------------------------------------
        if installment_years and installment_years > 0:
            if payment_type == "cash":
                # Contradiction: cash with 7 years installments -> reconcile to "both" or "installments"
                reconciled["payment_type"] = "both"
                warnings.append("Promoted payment_type to 'both' due to explicit installment_years presence.")
            elif not payment_type:
                reconciled["payment_type"] = "installments"

        if down_payment_amount and down_payment_amount > 0 and not payment_type:
            reconciled["payment_type"] = "installments"

        # ------------------------------------------------------------------
        # 2. Down Payment Percentage vs Amount Validation
        # ------------------------------------------------------------------
        if down_payment_pct is not None:
            if down_payment_pct > 100.0 or down_payment_pct < 0.0:
                warnings.append(f"Invalid down_payment_pct {down_payment_pct}% rejected.")
                reconciled["down_payment_pct"] = None

        if down_payment_amount and price and price > 0:
            if down_payment_amount >= price * 0.90:
                warnings.append(f"Down payment ({down_payment_amount}) >= 90% of price ({price}); rejected as likely false positive.")
                reconciled["down_payment_amount"] = None

        # ------------------------------------------------------------------
        # 3. Delivery Status vs Delivery Date Reconciliation
        # ------------------------------------------------------------------
        if delivery_status == "ready":
            if delivery_date is not None:
                # Ready properties don't have future delivery dates
                warnings.append(f"Cleared delivery_date '{delivery_date}' for ready-to-move property.")
                reconciled["delivery_date"] = None

        if delivery_date is not None and not delivery_status:
            # Future delivery date implies off-plan
            reconciled["delivery_status"] = "off-plan"

        # ------------------------------------------------------------------
        # 4. Cash Discount Percentage Bounds
        # ------------------------------------------------------------------
        cash_discount = reconciled.get("cash_discount_pct")
        if cash_discount is not None:
            if cash_discount > 70.0 or cash_discount < 0.0:
                warnings.append(f"Suspicious cash discount {cash_discount}% rejected.")
                reconciled["cash_discount_pct"] = None

        return reconciled, warnings


consistency_validator = ListingConsistencyValidator()
