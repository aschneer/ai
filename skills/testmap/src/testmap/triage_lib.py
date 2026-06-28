"""Risk triage: collect six signals per symbol, score, and bucket (PRD 4).

Triage is a reproducible pure function of the index, the sensitivity keyword list,
git churn, and the prior analysis set. Each signal is normalized to 0..1, combined
with fixed weights into a composite score, and bucketed high/medium/low.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Signal weights (sum to 1.0). Sensitivity and complexity dominate; the binary
# flags and churn refine. Tuned for a directional ranking, not precise scoring.
_WEIGHTS = {
    "sensitivity": 0.30,
    "complexity": 0.25,
    "error_paths": 0.15,
    "public_api": 0.10,
    "churn": 0.10,
    "no_analysis": 0.10,
}

# Saturation caps: values at or above the cap contribute the full normalized 1.0.
_COMPLEXITY_CAP = 20
_CHURN_CAP = 20

_HIGH_THRESHOLD = 0.60
_MEDIUM_THRESHOLD = 0.30


def parse_sensitivity_keywords(markdown: str) -> list[str]:
    """Extract the backticked keyword tokens from sensitivity_keywords.md."""
    return sorted({match.lower() for match in re.findall(r"`([^`]+)`", markdown)})


def match_sensitivity(qualified_name: str, file_path: str, keywords: list[str]) -> list[str]:
    """Return keywords that appear as substrings of the symbol name or path."""
    haystack = f"{qualified_name} {file_path}".lower()
    return [keyword for keyword in keywords if keyword in haystack]


def triage_symbol(
    symbol: dict[str, Any],
    *,
    sensitivity_matches: list[str],
    churn: int | None,
    has_prior_analysis: bool,
) -> dict[str, Any]:
    """Build one triage record (signals, composite score, priority) for a symbol."""
    signals = {
        "cyclomatic_complexity": symbol["cyclomatic_complexity"],
        "has_error_paths": symbol["has_error_paths"],
        "sensitivity_match": sensitivity_matches,
        "churn": churn,
        "no_analysis": not has_prior_analysis,
        "public_api": symbol["visibility"] == "public",
    }
    score = _composite_score(signals)
    return {"priority": _bucket(score), "score": round(score, 4), "signals": signals}


def _composite_score(signals: dict[str, Any]) -> float:
    """Combine normalized signals with fixed weights into a 0..1 score."""
    normalized = {
        "sensitivity": 1.0 if signals["sensitivity_match"] else 0.0,
        "complexity": _saturate(signals["cyclomatic_complexity"], _COMPLEXITY_CAP),
        "error_paths": 1.0 if signals["has_error_paths"] else 0.0,
        "public_api": 1.0 if signals["public_api"] else 0.0,
        "churn": _saturate(signals["churn"] or 0, _CHURN_CAP),
        "no_analysis": 1.0 if signals["no_analysis"] else 0.0,
    }
    return sum(_WEIGHTS[name] * value for name, value in normalized.items())


def _saturate(value: int, cap: int) -> float:
    """Normalize a count to 0..1, clamping at ``cap``."""
    return min(value, cap) / cap


def _bucket(score: float) -> str:
    """Map a composite score to a priority bucket."""
    if score >= _HIGH_THRESHOLD:
        return "high"
    if score >= _MEDIUM_THRESHOLD:
        return "medium"
    return "low"
