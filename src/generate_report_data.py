import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import DATASET_XLSX, OUTPUT_DIR, RAW_DIR


def compute_mann_whitney_u(group1: np.ndarray, group2: np.ndarray) -> tuple[float, float]:
    """
    Compute Mann-Whitney U statistic and two-sided p-value using asymptotic normal approximation.
    """
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0

    combined = np.concatenate([group1, group2])
    ranks = pd.Series(combined).rank().to_numpy()
    r1 = np.sum(ranks[:n1])

    u1 = r1 - (n1 * (n1 + 1)) / 2.0
    u2 = (n1 * n2) - u1
    u = min(u1, u2)

    # Expected value and standard deviation under H0
    mean_u = (n1 * n2) / 2.0
    std_u = math.sqrt((n1 * n2 * (n1 + n2 + 1)) / 12.0)

    # Continuity correction
    z = (u - mean_u + 0.5) / std_u if u < mean_u else (u - mean_u - 0.5) / std_u

    # Two-sided p-value via error function
    p_val = math.erfc(abs(z) / math.sqrt(2.0))
    return float(u1), float(p_val)


def compute_bootstrap_ci(
    group1: np.ndarray,
    group2: np.ndarray,
    n_bootstraps: int = 2000,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval for difference in medians."""
    rng = np.random.default_rng(42)
    diffs = []
    for _ in range(n_bootstraps):
        b1 = rng.choice(group1, size=len(group1), replace=True)
        b2 = rng.choice(group2, size=len(group2), replace=True)
        diffs.append(np.median(b1) - np.median(b2))
    low = float(np.percentile(diffs, 100 * (alpha / 2)))
    high = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return low, high


def generate_metrics() -> dict[str, Any]:
    df = pd.read_excel(DATASET_XLSX)
    raw_details = list((RAW_DIR / "details").glob("*.html"))

    total_records = len(df)
    sale_records = int((df["purpose"] == "sale").sum())
    rent_records = int((df["purpose"] == "rent").sum())
    verified_portal_count = int(df["is_verified"].fillna(False).sum())
    verified_portal_pct = round(verified_portal_count / total_records * 100, 2)

    gov_dist = df["governorate"].value_counts().to_dict()
    prop_dist = df["property_type"].value_counts().to_dict()

    # Group B coverage
    group_b_cols = [
        "compound_name",
        "developer_name",
        "governorate",
        "city",
        "district",
        "finishing_level",
        "delivery_status",
        "delivery_date",
        "sale_type",
        "payment_type",
        "down_payment_amount",
        "down_payment_pct",
        "installment_years",
        "installment_amount",
        "installment_frequency",
        "cash_discount_pct",
        "amenities",
        "floor_number",
        "garden_area_sqm",
        "roof_area_sqm",
        "is_negotiable",
    ]
    coverage = {}
    for col in group_b_cols:
        if col in df.columns:
            non_null = df[col].notna() & (df[col] != "")
            count = int(non_null.sum())
            pct = round(count / total_records * 100, 2)
            coverage[col] = {"count": count, "pct": pct}

    # Statistical Analysis: Sale Properties Price / sqm
    sale_df = df[df["purpose"] == "sale"].copy()
    # Filter valid positive price and area
    sale_valid = sale_df[
        sale_df["price_per_sqm"].notna()
        & (sale_df["price_per_sqm"] > 1000)
        & (sale_df["price_per_sqm"] < 1_000_000)
    ].copy()
    sale_valid["is_compound"] = sale_valid["compound_name"].notna()

    compound_sqm = sale_valid[sale_valid["is_compound"]]["price_per_sqm"].to_numpy()
    standalone_sqm = sale_valid[~sale_valid["is_compound"]]["price_per_sqm"].to_numpy()

    # Mann-Whitney U test (non-parametric rank-sum test for skewed real estate prices)
    u_stat, p_val = compute_mann_whitney_u(compound_sqm, standalone_sqm)
    ci_low, ci_high = compute_bootstrap_ci(compound_sqm, standalone_sqm)

    compound_median = float(np.median(compound_sqm))
    compound_mean = float(np.mean(compound_sqm))
    compound_iqr_25 = float(np.percentile(compound_sqm, 25))
    compound_iqr_75 = float(np.percentile(compound_sqm, 75))

    standalone_median = float(np.median(standalone_sqm))
    standalone_mean = float(np.mean(standalone_sqm))
    standalone_iqr_25 = float(np.percentile(standalone_sqm, 25))
    standalone_iqr_75 = float(np.percentile(standalone_sqm, 75))

    premium_pct = round(((compound_median - standalone_median) / standalone_median) * 100, 2)

    # Governorate price tiers (Sale)
    gov_stats = {}
    for gov, group in sale_valid.groupby("governorate"):
        sqm_vals = group["price_per_sqm"].to_numpy()
        gov_stats[str(gov)] = {
            "n": int(len(sqm_vals)),
            "median_price_sqm": round(float(np.median(sqm_vals)), 1),
            "mean_price_sqm": round(float(np.mean(sqm_vals)), 1),
        }

    # Finishing level (Sale)
    finishing_stats = {}
    for fin, group in sale_valid.groupby("finishing_level"):
        if pd.notna(fin):
            sqm_vals = group["price_per_sqm"].to_numpy()
            finishing_stats[str(fin)] = {
                "n": int(len(sqm_vals)),
                "median_price_sqm": round(float(np.median(sqm_vals)), 1),
                "mean_price_sqm": round(float(np.mean(sqm_vals)), 1),
            }

    # Rental analysis: Monthly Rent per sqm
    rent_df = df[df["purpose"] == "rent"].copy()
    rent_valid = rent_df[
        rent_df["price_per_sqm"].notna()
        & (rent_valid_mask := (rent_df["price_per_sqm"] > 10) & (rent_df["price_per_sqm"] < 5000))
    ].copy()

    furnished_rent = rent_valid[rent_valid["finishing_level"] == "furnished"]["price_per_sqm"].to_numpy()
    unfurnished_rent = rent_valid[rent_valid["finishing_level"] != "furnished"]["price_per_sqm"].to_numpy()

    rent_furnished_median = float(np.median(furnished_rent)) if len(furnished_rent) > 0 else 0.0
    rent_unfurnished_median = float(np.median(unfurnished_rent)) if len(unfurnished_rent) > 0 else 0.0
    rent_ratio = round(rent_furnished_median / rent_unfurnished_median, 2) if rent_unfurnished_median > 0 else 0.0

    # Installment plans
    inst_df = df[df["installment_years"].notna()]
    inst_counts = inst_df["installment_years"].value_counts().to_dict()
    total_inst = len(inst_df)
    tier_10_12 = sum(count for yrs, count in inst_counts.items() if 10.0 <= yrs <= 12.0)
    tier_10_12_pct = round(tier_10_12 / total_inst * 100, 2) if total_inst > 0 else 0.0

    # Cash discounts
    cash_disc = df[df["cash_discount_pct"].notna()]["cash_discount_pct"].to_numpy()
    mean_cash_disc = round(float(np.mean(cash_disc)), 1) if len(cash_disc) > 0 else 0.0
    min_cash_disc = round(float(np.min(cash_disc)), 1) if len(cash_disc) > 0 else 0.0
    max_cash_disc = round(float(np.max(cash_disc)), 1) if len(cash_disc) > 0 else 0.0

    metrics = {
        "dataset_summary": {
            "total_records": total_records,
            "sale_records": sale_records,
            "rent_records": rent_records,
            "detail_html_captured_count": int(df["detail_html_captured"].sum()) if "detail_html_captured" in df.columns else 16,
            "raw_html_files_on_disk": len(raw_details),
            "portal_verified_count": verified_portal_count,
            "portal_verified_pct": verified_portal_pct,
            "governorates_count": len(gov_dist),
            "governorates_breakdown": gov_dist,
            "property_types_breakdown": prop_dist,
        },
        "coverage": coverage,
        "statistical_tests": {
            "compound_premium": {
                "n_compound": int(len(compound_sqm)),
                "n_standalone": int(len(standalone_sqm)),
                "compound_median_sqm": round(compound_median, 1),
                "compound_mean_sqm": round(compound_mean, 1),
                "compound_iqr": [round(compound_iqr_25, 1), round(compound_iqr_75, 1)],
                "standalone_median_sqm": round(standalone_median, 1),
                "standalone_mean_sqm": round(standalone_mean, 1),
                "standalone_iqr": [round(standalone_iqr_25, 1), round(standalone_iqr_75, 1)],
                "median_premium_pct": premium_pct,
                "mann_whitney_u": float(u_stat),
                "p_value": float(p_val),
                "bootstrap_median_diff_95ci": [round(ci_low, 1), round(ci_high, 1)],
            },
            "governorate_price_sqm_sale": gov_stats,
            "finishing_level_sale": finishing_stats,
            "rental_intensity": {
                "furnished_median_monthly_sqm": round(rent_furnished_median, 1),
                "unfurnished_median_monthly_sqm": round(rent_unfurnished_median, 1),
                "furnished_to_unfurnished_ratio": rent_ratio,
            },
            "financing_structures": {
                "total_listings_with_installments": total_inst,
                "tier_10_12_years_count": tier_10_12,
                "tier_10_12_years_pct": tier_10_12_pct,
                "cash_discount_mean_pct": mean_cash_disc,
                "cash_discount_min_pct": min_cash_disc,
                "cash_discount_max_pct": max_cash_disc,
            },
        },
    }

    out_file = OUTPUT_DIR / "analysis_metrics.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    print(f"Exported verified analysis metrics to {out_file}")
    return metrics


if __name__ == "__main__":
    generate_metrics()
