"""
==============================================================================
ECES Take-Home: Gemini 3.1 Flash-Lite Auditor & Semantic Refiner
==============================================================================
Hybrid Tier: Serves as a semantic refiner and auditor for deterministic extractions.
Only queries the model when critical fields remain unresolved or ambiguous.
All outputs are strictly verified through Tier-3 Verbatim Evidence Verifier.
==============================================================================
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


class GeminiRefiner:
    """Hybrid Semantic Refiner & Auditor using Gemini 3.1 Flash-Lite."""

    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name or GEMINI_MODEL
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        self.total_prompt_tokens = 0
        self.total_candidate_tokens = 0
        self.total_thought_tokens = 0
        self.total_calls = 0
        self.total_time_sec = 0.0

    def refine_listing(
        self,
        description_raw: str | None,
        title: str | None,
        current_predictions: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Audits and refines missing/ambiguous fields using Gemini 3.1.
        Returns a refined dictionary of field values.
        """
        if not description_raw and not title:
            return current_predictions

        text = f"{title or ''}\n{description_raw or ''}".strip()
        if len(text) < 15:
            return current_predictions

        # Identify which key fields need semantic refinement
        needs_refinement = (
            current_predictions.get("compound_name") is None
            or current_predictions.get("developer_name") is None
            or current_predictions.get("finishing_level") is None
            or current_predictions.get("payment_type") is None
            or current_predictions.get("sale_type") is None
            or current_predictions.get("delivery_status") is None
            or (current_predictions.get("installment_years") is None and ("قسط" in text or "تقسيط" in text or "سنين" in text or "سنوات" in text))
        )

        if not needs_refinement:
            return current_predictions

        prompt = f"""You are an expert Egyptian Real Estate Data Engineering Auditor.
Analyze this property listing description and extract missing Group B variables.

STRICT RULES:
1. Honest Null Mandate: If a field is not explicitly stated in the text, return null. Do NOT assume, speculate, or fabricate unstated delivery dates or developers.
2. Output exact verbatim terms where possible.
3. Convert numbers to numeric floats (e.g. '1.5M' or 'مليون ونص' -> 1500000).

Current Initial Extraction:
{json.dumps({k: current_predictions.get(k) for k in ['compound_name', 'developer_name', 'finishing_level', 'delivery_status', 'delivery_date', 'sale_type', 'payment_type', 'down_payment_pct', 'installment_years'] if k in current_predictions}, ensure_ascii=False)}

Listing Text:
{text[:1500]}

Respond with JSON only:
{{
  "compound_name": null or string,
  "developer_name": null or string,
  "finishing_level": null or string (one of: "super lux", "fully finished", "semi-finished", "core & shell", "furnished"),
  "delivery_status": null or string (one of: "ready", "off_plan"),
  "delivery_date": null or string,
  "sale_type": null or string (one of: "primary", "resale"),
  "payment_type": null or string (one of: "cash", "installments", "cash or installments"),
  "down_payment_pct": null or float,
  "installment_years": null or float
}}
"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.0,
            },
        }

        start = time.time()
        try:
            resp = requests.post(self.url, json=payload, timeout=15)
            self.total_time_sec += time.time() - start
            self.total_calls += 1

            if resp.status_code == 200:
                data = resp.json()
                usage = data.get("usageMetadata", {})
                self.total_prompt_tokens += usage.get("promptTokenCount", 0)
                self.total_candidate_tokens += usage.get("candidatesTokenCount", 0)
                self.total_thought_tokens += usage.get("thoughtsTokenCount", 0)

                raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
                refined_dict = json.loads(raw_json)

                # Merge non-null refinements for missing fields
                merged = dict(current_predictions)
                for k, v in refined_dict.items():
                    if merged.get(k) is None and v is not None:
                        merged[k] = v
                return merged

        except Exception as e:
            # On timeout or network error, fallback gracefully to deterministic values
            pass

        return current_predictions

    def get_cost_summary(self) -> dict[str, Any]:
        """Compute total token and USD cost summary."""
        # Gemini 3.1 Flash-Lite Pricing: $0.075 / 1M prompt tokens, $0.30 / 1M candidate tokens
        cost_usd = (self.total_prompt_tokens / 1_000_000.0 * 0.075) + (self.total_candidate_tokens / 1_000_000.0 * 0.30)
        return {
            "model_name": self.model_name,
            "total_calls": self.total_calls,
            "prompt_tokens": self.total_prompt_tokens,
            "candidates_tokens": self.total_candidate_tokens,
            "thoughts_tokens": self.total_thought_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_candidate_tokens + self.total_thought_tokens,
            "total_cost_usd": round(cost_usd, 6),
            "total_time_sec": round(self.total_time_sec, 2),
        }
