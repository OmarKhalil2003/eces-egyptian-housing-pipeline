#!/usr/bin/env python3
"""
==============================================================================
ECES Take-Home: Comparative Scraping & Extraction Methodology Benchmark
==============================================================================
Runs an empirical head-to-head evaluation of multiple scraping and parsing techniques:
  1. Technique A: BeautifulSoup 4 DOM Tree Parsing & Microdata Scraper
  2. Technique B: Deterministic Egyptian Real Estate Regex & Gazetteer Engine
  3. Technique C: Gemini 3.6 Flash Structured Semantic LLM Extractor

Evaluates all techniques against the 25 Hand-Labeled Gold Standard listings.
Computes:
  - Accuracy, Precision, Recall, Hallucination Rate per field
  - Execution Latency (seconds / listing)
  - Token Accounting & USD Dollar Cost
==============================================================================
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import bs4
import requests

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from src.detail_parser import BayutDetailParser
from src.normalizer import normalize_text, parse_arabic_amount
from src.parser import BayutParser
from src.rules import ListingRulesParser

GOLD_PATH = BASE_DIR / "evaluation" / "gold_25.json"
DETAILS_DIR = BASE_DIR / "data" / "raw" / "details"
OUTPUT_BENCHMARK_PATH = BASE_DIR / "evaluation" / "methodology_benchmark.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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
    "amenities",
    "floor_number",
    "garden_area_sqm",
    "roof_area_sqm",
    "is_negotiable",
]


# ==============================================================================
# Helper Functions
# ==============================================================================

def normalize_val(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    if isinstance(val, list):
        return sorted([str(x).strip().lower() for x in val if x])
    s = str(val).strip().lower()
    return s if s not in ("", "none", "null", "n/a") else None


def compare_field(pred: Any, truth: Any, field_name: str) -> bool:
    p = normalize_val(pred)
    t = normalize_val(truth)

    if p is None and t is None:
        return True
    if p is None or t is None:
        return False

    if isinstance(t, (int, float)) and isinstance(p, (int, float)):
        return abs(float(p) - float(t)) <= 0.05

    if field_name == "amenities" and isinstance(t, list) and isinstance(p, list):
        if not t and not p:
            return True
        if not t or not p:
            return False
        overlap = set(p) & set(t)
        return len(overlap) >= 1

    return str(p) == str(t) or str(p) in str(t) or str(t) in str(p)


def evaluate_predictions(gold_records: list[dict], pred_map: dict[str, dict]) -> dict[str, Any]:
    field_metrics = {}
    total_acc_sum = 0.0
    total_halluc_sum = 0.0
    valid_halluc_fields = 0

    for field in GROUP_B_FIELDS:
        correct = 0
        tp = 0
        fp = 0
        fn = 0
        null_truth_count = 0
        hallucinations = 0
        support_pos = 0

        for g in gold_records:
            gid = str(g["listing_id"])
            p = pred_map.get(gid, {})
            g_val = g.get(field)
            p_val = p.get(field)

            is_match = compare_field(p_val, g_val, field)
            if is_match:
                correct += 1

            if g_val is not None:
                support_pos += 1
                if p_val is not None:
                    if is_match:
                        tp += 1
                    else:
                        fp += 1
                else:
                    fn += 1
            else:
                null_truth_count += 1
                if p_val is not None:
                    hallucinations += 1

        acc_pct = (correct / len(gold_records)) * 100.0
        total_acc_sum += acc_pct

        prec = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else (100.0 if support_pos == 0 else 0.0)
        rec = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else (100.0 if support_pos == 0 else 0.0)
        halluc_pct = (hallucinations / null_truth_count * 100.0) if null_truth_count > 0 else 0.0

        if null_truth_count > 0:
            total_halluc_sum += halluc_pct
            valid_halluc_fields += 1

        field_metrics[field] = {
            "accuracy": round(acc_pct, 1),
            "precision": round(prec, 1),
            "recall": round(rec, 1),
            "hallucination_rate": round(halluc_pct, 1),
            "support_positive_n": support_pos,
        }

    overall_accuracy = total_acc_sum / len(GROUP_B_FIELDS)
    overall_hallucination = (total_halluc_sum / valid_halluc_fields) if valid_halluc_fields > 0 else 0.0

    return {
        "overall_accuracy_pct": round(overall_accuracy, 1),
        "overall_hallucination_rate_pct": round(overall_hallucination, 1),
        "fields": field_metrics,
    }


# ==============================================================================
# Technique A: BeautifulSoup DOM Parser
# ==============================================================================

def run_technique_bs4(gold_records: list[dict]) -> tuple[dict[str, dict], float]:
    """Pure BeautifulSoup4 DOM tree extraction on cached HTML."""
    start_time = time.time()
    predictions = {}

    for g in gold_records:
        gid = str(g["listing_id"])
        html_file = DETAILS_DIR / f"{gid}.html"
        record_pred = {f: None for f in GROUP_B_FIELDS}

        if html_file.exists():
            html_text = html_file.read_text(encoding="utf-8", errors="ignore")
            soup = bs4.BeautifulSoup(html_text, "html.parser")

            # Extract description text from DOM selectors
            desc_el = (
                soup.select_one('[aria-label="Property description"]')
                or soup.select_one('[aria-label="وصف العقار"]')
                or soup.select_one('div[class*="description"]')
            )
            desc_text = desc_el.get_text(strip=True, separator=" ") if desc_el else ""

            # Extract basic fields using BS4 table selectors & naive keywords
            if "كمبوند" in desc_text or "compound" in desc_text.lower():
                m = re.search(r"(?:كمبوند|compound)\s+([A-Za-z\u0600-\u06FF\s]+?)(?:\n|\.|\,|\s{2,})", desc_text, re.IGNORECASE)
                if m:
                    record_pred["compound_name"] = m.group(1).strip()

            if "متشطب" in desc_text or "fully finished" in desc_text.lower():
                record_pred["finishing_level"] = "fully finished"
            elif "نصف تشطيب" in desc_text or "semi finished" in desc_text.lower():
                record_pred["finishing_level"] = "semi-finished"
            elif "سوبر لوكس" in desc_text or "super lux" in desc_text.lower():
                record_pred["finishing_level"] = "super lux"

            if "استلام فوري" in desc_text or "ready" in desc_text.lower():
                record_pred["delivery_status"] = "ready"
            elif "تحت الانشاء" in desc_text or "off plan" in desc_text.lower():
                record_pred["delivery_status"] = "off_plan"

            # Parse simple numbers
            dp_m = re.search(r"مقدم\s*([0-9\.,]+%?)", desc_text)
            if dp_m:
                dp_str = dp_m.group(1)
                if "%" in dp_str:
                    try:
                        record_pred["down_payment_pct"] = float(dp_str.replace("%", "").strip())
                    except ValueError:
                        pass

        predictions[gid] = record_pred

    latency = (time.time() - start_time) / len(gold_records)
    return predictions, latency


# ==============================================================================
# Technique B: Deterministic Rules & Gazetteer Engine (Our Baseline)
# ==============================================================================

def run_technique_rules(gold_records: list[dict]) -> tuple[dict[str, dict], float]:
    """Our 3-tier deterministic rules + gazetteer + evidence verifier engine."""
    start_time = time.time()
    parser = BayutParser()
    detail_parser = BayutDetailParser()
    predictions = {}

    for g in gold_records:
        gid = str(g["listing_id"])
        html_file = DETAILS_DIR / f"{gid}.html"
        detail_data = None
        if html_file.exists():
            detail_data = detail_parser.parse_file(str(html_file))
        raw = {"id": gid, "externalID": gid, "purpose": "for-sale"}
        parsed = parser.parse(raw=raw, detail=detail_data)
        predictions[gid] = parsed.model_dump()

    latency = (time.time() - start_time) / len(gold_records)
    return predictions, latency


# ==============================================================================
# Technique C: Gemini 3.6 Flash Structured Semantic LLM Extractor
# ==============================================================================

def run_technique_gemini(gold_records: list[dict]) -> tuple[dict[str, dict], float, dict[str, Any]]:
    """Gemini 3.6 Flash extraction via Google Generative AI REST API."""
    start_time = time.time()
    predictions = {}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"

    total_prompt_tokens = 0
    total_candidate_tokens = 0
    total_thought_tokens = 0
    api_calls_count = 0

    print("\nExecuting Gemini 3.6 Flash extraction over 25 gold listings...")

    for idx, g in enumerate(gold_records, 1):
        gid = str(g["listing_id"])
        html_file = DETAILS_DIR / f"{gid}.html"
        desc_text = ""

        if html_file.exists():
            html_text = html_file.read_text(encoding="utf-8", errors="ignore")
            soup = bs4.BeautifulSoup(html_text, "html.parser")
            desc_el = (
                soup.select_one('[aria-label="Property description"]')
                or soup.select_one('[aria-label="وصف العقار"]')
                or soup.select_one('div[class*="description"]')
            )
            if desc_el:
                desc_text = desc_el.get_text(strip=True, separator=" ")

        prompt = f"""You are an expert Egyptian Real Estate Data Engineer.
Extract Group B variables from this Egyptian property listing into strict JSON.
Rules:
- If a value is not explicitly stated in the text, return null. Do NOT invent dates or developers.
- Numbers must be numeric floats or integers (e.g. '1.5M' or 'مليون ونص' -> 1500000).

Input Listing Description:
{desc_text if desc_text else "No description available."}

Respond with JSON only adhering to this structure:
{{
  "compound_name": null or string,
  "developer_name": null or string,
  "governorate": null or string,
  "city": null or string,
  "district": null or string,
  "finishing_level": null or string (e.g. "super lux", "fully finished", "semi-finished", "core & shell", "furnished"),
  "delivery_status": null or string ("ready" or "off_plan"),
  "delivery_date": null or string,
  "sale_type": null or string ("primary" or "resale"),
  "payment_type": null or string ("cash", "installments", "cash or installments"),
  "down_payment_amount": null or float,
  "down_payment_pct": null or float,
  "installment_years": null or float,
  "amenities": list of strings,
  "floor_number": null or integer,
  "garden_area_sqm": null or float,
  "roof_area_sqm": null or float,
  "is_negotiable": null or boolean
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        }

        record_pred = {f: None for f in GROUP_B_FIELDS}

        try:
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usageMetadata", {})
                total_prompt_tokens += usage.get("promptTokenCount", 0)
                total_candidate_tokens += usage.get("candidatesTokenCount", 0)
                total_thought_tokens += usage.get("thoughtsTokenCount", 0)
                api_calls_count += 1

                raw_json_str = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed_json = json.loads(raw_json_str)
                record_pred.update({k: parsed_json.get(k) for k in GROUP_B_FIELDS if k in parsed_json})
            else:
                print(f"  [Warning] Gemini API returned {resp.status_code} on record {gid}: {resp.text[:100]}")
        except Exception as e:
            print(f"  [Error] Gemini request exception on record {gid}: {e}")

        predictions[gid] = record_pred
        print(f"  ▶ Processed [{idx}/25] (Listing {gid}) with Gemini 3.6 Flash...")
        # Polite rate pacing for free tier limits
        time.sleep(1.2)

    total_time = time.time() - start_time
    latency = total_time / len(gold_records)

    # Gemini 1.5/2.5/3.6 Flash Pricing ($0.075 / 1M prompt tokens, $0.30 / 1M candidate tokens)
    cost_usd = (total_prompt_tokens / 1_000_000.0 * 0.075) + (total_candidate_tokens / 1_000_000.0 * 0.30)

    token_summary = {
        "api_calls": api_calls_count,
        "prompt_tokens": total_prompt_tokens,
        "candidates_tokens": total_candidate_tokens,
        "thoughts_tokens": total_thought_tokens,
        "total_tokens": total_prompt_tokens + total_candidate_tokens + total_thought_tokens,
        "total_cost_usd": round(cost_usd, 6),
        "total_wall_clock_time_sec": round(total_time, 2),
    }

    return predictions, latency, token_summary


# ==============================================================================
# Technique D: Hybrid Deterministic Core + Gemini 3.1 Flash-Lite Refiner
# ==============================================================================

def run_technique_hybrid(gold_records: list[dict]) -> tuple[dict[str, dict], float, dict[str, Any]]:
    """Hybrid Architecture: Deterministic Rules baseline + Gemini 3.1 Flash-Lite auditor/refiner."""
    from src.gemini_refiner import GeminiRefiner
    from src.evidence_verifier import evidence_verifier

    start_time = time.time()
    parser = BayutParser()
    detail_parser = BayutDetailParser()
    refiner = GeminiRefiner(model_name="gemini-3.1-flash-lite")
    predictions = {}

    print("\nExecuting Hybrid Architecture (Rules + Gemini 3.1 Refiner) on 25 gold listings...")

    for idx, g in enumerate(gold_records, 1):
        gid = str(g["listing_id"])
        html_file = DETAILS_DIR / f"{gid}.html"
        detail_data = None
        desc_text = ""
        if html_file.exists():
            detail_data = detail_parser.parse_file(str(html_file))
            desc_text = detail_data.get("description_raw") or ""

        raw = {"id": gid, "externalID": gid, "purpose": "for-sale"}
        base_parsed = parser.parse(raw=raw, detail=detail_data).model_dump()

        # Step 2: Semantic refinement on missing/ambiguous attributes
        refined_dict = refiner.refine_listing(
            description_raw=desc_text,
            title=raw.get("title", ""),
            current_predictions=base_parsed,
        )

        # Step 3: Tier-3 Verbatim Evidence Verification on refined candidates
        source_text = f"{raw.get('title', '')} {desc_text}".strip()
        for field in ("compound_name", "developer_name", "finishing_level", "delivery_status", "delivery_date", "sale_type", "payment_type"):
            ref_val = refined_dict.get(field)
            if ref_val is not None and base_parsed.get(field) is None:
                _, verified_val, _ = evidence_verifier.verify_field(field, ref_val, None, source_text)
                base_parsed[field] = verified_val
            elif ref_val is not None:
                base_parsed[field] = ref_val

        predictions[gid] = base_parsed
        print(f"  ▶ Processed [{idx}/25] (Listing {gid}) with Hybrid Engine...")
        time.sleep(0.5)

    total_time = time.time() - start_time
    latency = total_time / len(gold_records)
    token_summary = refiner.get_cost_summary()

    return predictions, latency, token_summary


# ==============================================================================
# Main Benchmark Orchestrator
# ==============================================================================

def main() -> None:
    print("=" * 80)
    print("ECES TAKE-HOME METHODOLOGY & TECHNIQUE COMPARATIVE BENCHMARK")
    print("=" * 80)

    if not GOLD_PATH.exists():
        print(f"Error: Gold standard not found at {GOLD_PATH}")
        sys.exit(1)

    with open(GOLD_PATH, "r", encoding="utf-8") as f:
        gold_records = json.load(f)

    print(f"Loaded {len(gold_records)} hand-labeled gold records.")

    # 1. Technique A: BeautifulSoup DOM Parser
    print("\n--- Running Technique A: BeautifulSoup DOM Parser ---")
    preds_bs4, latency_bs4 = run_technique_bs4(gold_records)
    eval_bs4 = evaluate_predictions(gold_records, preds_bs4)
    print(f"✔ BS4 Overall Accuracy: {eval_bs4['overall_accuracy_pct']}% | Hallucination Rate: {eval_bs4['overall_hallucination_rate_pct']}% | Latency: {latency_bs4*1000:.2f}ms/item")

    # 2. Technique B: Deterministic Rules & Gazetteers (Our Engine)
    print("\n--- Running Technique B: Deterministic Rules & Gazetteer Engine ---")
    preds_rules, latency_rules = run_technique_rules(gold_records)
    eval_rules = evaluate_predictions(gold_records, preds_rules)
    print(f"✔ Rules Overall Accuracy: {eval_rules['overall_accuracy_pct']}% | Hallucination Rate: {eval_rules['overall_hallucination_rate_pct']}% | Latency: {latency_rules*1000:.2f}ms/item")

    # 3. Technique C: Gemini 3.6 Flash API
    print("\n--- Running Technique C: Gemini 3.6 Flash Structured LLM ---")
    preds_gemini, latency_gemini, token_summary_gemini = run_technique_gemini(gold_records)
    eval_gemini = evaluate_predictions(gold_records, preds_gemini)
    print(f"✔ Gemini Overall Accuracy: {eval_gemini['overall_accuracy_pct']}% | Hallucination Rate: {eval_gemini['overall_hallucination_rate_pct']}% | Latency: {latency_gemini:.2f}s/item")

    # 4. Technique D: Hybrid Deterministic + Gemini 3.1 Refiner
    print("\n--- Running Technique D: Hybrid Deterministic + Gemini 3.1 Flash-Lite Refiner ---")
    preds_hybrid, latency_hybrid, token_summary_hybrid = run_technique_hybrid(gold_records)
    eval_hybrid = evaluate_predictions(gold_records, preds_hybrid)
    print(f"✔ Hybrid Overall Accuracy: {eval_hybrid['overall_accuracy_pct']}% | Hallucination Rate: {eval_hybrid['overall_hallucination_rate_pct']}% | Latency: {latency_hybrid:.2f}s/item")

    # Save consolidated benchmark JSON
    benchmark_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "gold_sample_size": len(gold_records),
        "techniques": {
            "technique_a_beautifulsoup_dom": {
                "name": "BeautifulSoup DOM Tree & Microdata Parser",
                "overall_accuracy_pct": eval_bs4["overall_accuracy_pct"],
                "overall_hallucination_rate_pct": eval_bs4["overall_hallucination_rate_pct"],
                "avg_latency_ms": round(latency_bs4 * 1000, 2),
                "cost_usd_per_listing": 0.0,
                "fields": eval_bs4["fields"],
            },
            "technique_b_deterministic_rules": {
                "name": "Deterministic Egyptian Rules, Gazetteers & Evidence Verifier",
                "overall_accuracy_pct": eval_rules["overall_accuracy_pct"],
                "overall_hallucination_rate_pct": eval_rules["overall_hallucination_rate_pct"],
                "avg_latency_ms": round(latency_rules * 1000, 2),
                "cost_usd_per_listing": 0.0,
                "fields": eval_rules["fields"],
            },
            "technique_c_gemini_llm": {
                "name": "Gemini 3.6 Flash Structured LLM Extractor",
                "overall_accuracy_pct": eval_gemini["overall_accuracy_pct"],
                "overall_hallucination_rate_pct": eval_gemini["overall_hallucination_rate_pct"],
                "avg_latency_sec": round(latency_gemini, 2),
                "token_usage": token_summary_gemini,
                "cost_usd_per_listing": round(token_summary_gemini["total_cost_usd"] / len(gold_records), 6),
                "fields": eval_gemini["fields"],
            },
            "technique_d_hybrid_gemini31": {
                "name": "Hybrid Deterministic Rules + Gemini 3.1 Flash-Lite Refiner",
                "overall_accuracy_pct": eval_hybrid["overall_accuracy_pct"],
                "overall_hallucination_rate_pct": eval_hybrid["overall_hallucination_rate_pct"],
                "avg_latency_sec": round(latency_hybrid, 2),
                "token_usage": token_summary_hybrid,
                "cost_usd_per_listing": round(token_summary_hybrid["total_cost_usd"] / len(gold_records), 6),
                "fields": eval_hybrid["fields"],
            },
        },
    }

    with open(OUTPUT_BENCHMARK_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 95)
    print("COMPARATIVE BENCHMARK SUMMARY TABLE (4 METHODOLOGIES)")
    print("=" * 95)
    print(f"{'Methodology':<45} {'Accuracy':<12} {'Hallucination Rate':<20} {'Latency':<14} {'Cost / Listing'}")
    print("-" * 95)
    cost_bs4 = 0.0
    cost_rules = 0.0
    cost_gemini = token_summary_gemini["total_cost_usd"] / len(gold_records)
    cost_hybrid = token_summary_hybrid["total_cost_usd"] / len(gold_records)

    print(f"{'1. BeautifulSoup DOM Parser':<45} {eval_bs4['overall_accuracy_pct']:>8.1f}% {eval_bs4['overall_hallucination_rate_pct']:>18.1f}% {latency_bs4*1000:>10.2f} ms {'$0.00 USD':>14}")
    print(f"{'2. Deterministic Rules & Gazetteers':<45} {eval_rules['overall_accuracy_pct']:>8.1f}% {eval_rules['overall_hallucination_rate_pct']:>18.1f}% {latency_rules*1000:>10.2f} ms {'$0.00 USD':>14}")
    print(f"{'3. Pure Gemini 3.6 Flash LLM':<45} {eval_gemini['overall_accuracy_pct']:>8.1f}% {eval_gemini['overall_hallucination_rate_pct']:>18.1f}% {latency_gemini:>10.2f} s {f'${cost_gemini:.6f} USD':>14}")
    print(f"{'4. Hybrid Rules + Gemini 3.1 Flash-Lite':<45} {eval_hybrid['overall_accuracy_pct']:>8.1f}% {eval_hybrid['overall_hallucination_rate_pct']:>18.1f}% {latency_hybrid:>10.2f} s {f'${cost_hybrid:.6f} USD':>14}")
    print("=" * 95)
    print(f"Exported detailed comparative report to: {OUTPUT_BENCHMARK_PATH}\n")


if __name__ == "__main__":
    main()
