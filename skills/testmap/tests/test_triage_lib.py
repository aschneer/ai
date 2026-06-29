"""Tests for risk triage scoring and bucketing."""

from __future__ import annotations

from testmap import triage_lib


def _symbol(cc: int = 1, err: bool = False, vis: str = "public") -> dict:
    return {"cyclomatic_complexity": cc, "has_error_paths": err, "visibility": vis}


def test_parse_sensitivity_keywords_extracts_backticked_tokens() -> None:
    md = "## Auth\n- `auth`, `token`\n\n**Risk:** ...\n- `password`\n"
    keywords = triage_lib.parse_sensitivity_keywords(md)
    assert {"auth", "token", "password"} <= set(keywords)


def test_parse_sensitivity_keywords_lowercases_and_dedupes() -> None:
    md = "- `Auth`\n- `auth`\n"
    assert triage_lib.parse_sensitivity_keywords(md) == ["auth"]


def test_match_sensitivity_substring_match() -> None:
    matched = triage_lib.match_sensitivity("authenticate_user", "src/x.py", ["auth", "pay"])
    assert matched == ["auth"]


def test_match_sensitivity_checks_file_path() -> None:
    matched = triage_lib.match_sensitivity("handler", "src/auth/login.py", ["auth"])
    assert matched == ["auth"]


def test_match_sensitivity_no_match() -> None:
    assert triage_lib.match_sensitivity("add", "src/calc.py", ["auth", "pay"]) == []


def test_triage_record_shape() -> None:
    record = triage_lib.triage_symbol(
        _symbol(), sensitivity_matches=[], churn=0, has_prior_analysis=True
    )
    assert set(record) == {"priority", "score", "signals"}
    assert record["priority"] in ("high", "medium", "low")


def test_high_risk_symbol_buckets_high() -> None:
    record = triage_lib.triage_symbol(
        _symbol(cc=18, err=True, vis="public"),
        sensitivity_matches=["auth", "token"],
        churn=12,
        has_prior_analysis=False,
    )
    assert record["priority"] == "high"


def test_trivial_private_symbol_buckets_low() -> None:
    record = triage_lib.triage_symbol(
        _symbol(cc=1, err=False, vis="private"),
        sensitivity_matches=[],
        churn=0,
        has_prior_analysis=True,
    )
    assert record["priority"] == "low"


def test_no_analysis_flag_captured() -> None:
    record = triage_lib.triage_symbol(
        _symbol(), sensitivity_matches=[], churn=0, has_prior_analysis=False
    )
    assert record["signals"]["no_analysis"] is True


def test_churn_none_is_preserved_and_scored_as_zero() -> None:
    record = triage_lib.triage_symbol(
        _symbol(cc=5), sensitivity_matches=[], churn=None, has_prior_analysis=True
    )
    assert record["signals"]["churn"] is None
    assert 0.0 <= record["score"] <= 1.0


def test_score_is_monotonic_in_complexity() -> None:
    low = triage_lib.triage_symbol(_symbol(cc=1), sensitivity_matches=[], churn=0, has_prior_analysis=True)
    high = triage_lib.triage_symbol(_symbol(cc=15), sensitivity_matches=[], churn=0, has_prior_analysis=True)
    assert high["score"] > low["score"]
