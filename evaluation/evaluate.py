from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import HousingListing
from src.parser import BayutParser


GROUP_B_FIELDS = [
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


LOCATION_SYNONYMS = {
    "القاهرة": "cairo",
    "cairo": "cairo",
    "مطروح": "matruh",
    "matruh": "matruh",
    "الجيزة": "giza",
    "giza": "giza",
    "الاسكندرية": "alexandria",
    "alexandria": "alexandria",
    "السويس": "suez",
    "suez": "suez",
    "البحر الاحمر": "red sea",
    "red sea": "red sea",
    "القاهرة الجديدة": "new cairo",
    "new cairo": "new cairo",
    "التجمع الخامس": "5th settlement",
    "الساحل الشمالي": "north coast",
    "north coast": "north coast",
    "الشيخ زايد": "sheikh zayed",
    "sheikh zayed": "sheikh zayed",
    "السادس من اكتوبر": "6th of october",
    "6th of october": "6th of october",
    "6th of october city": "6th of october",
    "العين السخنة": "ain sokhna",
    "ain sokhna": "ain sokhna",
}


def compare_values(pred: Any, truth: Any, field_name: str) -> bool:
    if truth is None:
        if pred is None or pred == "" or (isinstance(pred, list) and len(pred) == 0):
            return True
        return False

    if pred is None:
        return False

    if field_name in ("governorate", "city", "district"):
        p_str = str(pred).strip().lower()
        t_str = str(truth).strip().lower()
        p_norm = LOCATION_SYNONYMS.get(p_str, p_str)
        t_norm = LOCATION_SYNONYMS.get(t_str, t_str)
        if p_norm == t_norm or p_norm in t_norm or t_norm in p_norm:
            return True
        # Check sub-words
        p_words = set(p_norm.replace("/", " ").replace("-", " ").split())
        t_words = set(t_norm.replace("/", " ").replace("-", " ").split())
        if p_words and t_words and (p_words.issubset(t_words) or t_words.issubset(p_words) or len(p_words.intersection(t_words)) > 0):
            return True
        return False

    if field_name == "amenities":
        # Jaccard overlap or subset match
        p_set = set(pred) if isinstance(pred, list) else set(str(pred).split(", "))
        t_set = set(truth) if isinstance(truth, list) else set(str(truth).split(", "))
        if not t_set and not p_set:
            return True
        if not t_set or not p_set:
            return False
        overlap = len(p_set.intersection(t_set))
        return overlap / max(len(t_set), 1) >= 0.5

    if isinstance(truth, (int, float)) and isinstance(pred, (int, float)):
        return abs(float(truth) - float(pred)) < 1e-3

    return str(pred).strip().lower() == str(truth).strip().lower()


def run_evaluation() -> dict[str, Any]:
    eval_dir = Path(__file__).resolve().parent
    gold_path = eval_dir / "gold_25.json"
    gold_preds_path = eval_dir / "gold_25_predictions.json"
    details_dir = eval_dir.parent / "data" / "raw" / "details"
    dataset_jsonl = eval_dir.parent / "data" / "output" / "egypt_housing_market_dataset.jsonl"

    if not gold_path.exists():
        raise FileNotFoundError(f"Gold dataset not found at {gold_path}")

    with open(gold_path, "r", encoding="utf-8") as f:
        gold_records = json.load(f)

    # Re-extract fresh predictions using BayutParser & BayutDetailParser
    from src.parser import BayutParser
    from src.detail_parser import BayutDetailParser
    parser = BayutParser()
    detail_parser = BayutDetailParser()

    all_records = []
    if dataset_jsonl.exists():
        with open(dataset_jsonl, "r", encoding="utf-8") as f:
            all_records = [json.loads(line) for line in f]
    record_map = {str(r.get("listing_id")): r for r in all_records}

    pred_records_list = []
    for g in gold_records:
        gid = str(g["listing_id"])
        raw = record_map.get(gid) or {"id": gid, "externalID": gid, "purpose": "for-sale"}
        html_file = None
        for candidate_id in (gid, str(raw.get("objectID") or ""), str(raw.get("id") or ""), str(raw.get("externalID") or "")):
            if candidate_id and candidate_id != "None":
                f = details_dir / f"{candidate_id}.html"
                if f.exists() and f.stat().st_size > 5000:
                    html_file = f
                    break

        detail_data = None
        if html_file and html_file.exists():
            try:
                detail_data = detail_parser.parse_file(str(html_file))
            except Exception:
                pass
        parsed_listing = parser.parse(raw=raw, detail=detail_data)
        pred_records_list.append(parsed_listing.model_dump())

    with open(gold_preds_path, "w", encoding="utf-8") as f:
        json.dump(pred_records_list, f, ensure_ascii=False, indent=2)

    pred_map = {str(r["listing_id"]): r for r in pred_records_list}

    results = []

    print("=" * 80)
    print("ECES TAKE-HOME PIPELINE EVALUATION ON 25 HAND-LABELED LISTINGS")
    print("=" * 80)
    print(f"{'Field Name':<25} {'Accuracy':<10} {'Support (n)':<12} {'Precision':<10} {'Recall':<10} {'Hallucination Rate':<18}")
    print("-" * 88)

    total_accuracy_sum = 0.0
    total_hallucination_sum = 0.0
    field_count = len(GROUP_B_FIELDS)

    field_metrics = {}

    for field in GROUP_B_FIELDS:
        correct = 0
        true_positives = 0
        false_positives = 0  # Predicted non-null when truth is null (Hallucination)
        false_negatives = 0  # Predicted null when truth is non-null
        pred_non_null = 0
        truth_non_null = 0
        truth_null = 0

        for gold in gold_records:
            listing_id = str(gold["listing_id"])
            pred_row = pred_map.get(listing_id, {})
            pred_val = pred_row.get(field)
            truth_val = gold.get(field)

            is_match = compare_values(pred_val, truth_val, field)

            if is_match:
                correct += 1

            if truth_val is not None and (not isinstance(truth_val, list) or len(truth_val) > 0):
                truth_non_null += 1
                if is_match:
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                truth_null += 1
                if pred_val is not None and pred_val != "" and (not isinstance(pred_val, list) or len(pred_val) > 0):
                    false_positives += 1

            if pred_val is not None and pred_val != "" and (not isinstance(pred_val, list) or len(pred_val) > 0):
                pred_non_null += 1

        acc = (correct / len(gold_records)) * 100.0
        prec = (true_positives / pred_non_null * 100.0) if pred_non_null > 0 else 100.0
        rec = (true_positives / truth_non_null * 100.0) if truth_non_null > 0 else 100.0
        hal_rate = (false_positives / truth_null * 100.0) if truth_null > 0 else 0.0

        total_accuracy_sum += acc
        total_hallucination_sum += hal_rate

        field_metrics[field] = {
            "accuracy": acc,
            "support_positive_n": truth_non_null,
            "precision": prec,
            "recall": rec,
            "hallucination_rate": hal_rate,
            "hallucinations_count": false_positives,
            "truth_null_count": truth_null,
        }

        print(f"{field:<25} {acc:>6.1f}%    {truth_non_null:>4}/25        {prec:>6.1f}%    {rec:>6.1f}%    {hal_rate:>6.1f}% ({false_positives}/{truth_null})")

    avg_acc = total_accuracy_sum / field_count
    avg_hal = total_hallucination_sum / field_count

    print("=" * 88)
    print(f"{'OVERALL AVERAGE':<25} {avg_acc:>6.1f}%                                               {avg_hal:>6.1f}%")
    print("=" * 88)

    summary_path = eval_dir / "evaluation_report.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "sample_size": len(gold_records),
                "overall_accuracy_pct": round(avg_acc, 2),
                "overall_hallucination_rate_pct": round(avg_hal, 2),
                "field_metrics": field_metrics,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\nSaved evaluation metrics to {summary_path}")

    return {
        "overall_accuracy": avg_acc,
        "overall_hallucination_rate": avg_hal,
        "field_metrics": field_metrics,
    }


if __name__ == "__main__":
    run_evaluation()
