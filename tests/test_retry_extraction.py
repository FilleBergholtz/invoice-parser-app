"""Unit tests for deterministic retry fallback."""

from src.pipeline.retry_extraction import run_deterministic_fallback


def test_run_deterministic_fallback_picks_best_confidence():
    confidences = {
        "aggressive": 0.6,
        "extended_patterns": 0.4,
        "broader_search": 0.8,
    }

    def extract(strategy=None):
        return {"confidence": confidences.get(strategy, 0.0)}

    result, best_confidence, attempts = run_deterministic_fallback(
        extract_func=extract,
        target_confidence=0.95,
        max_attempts=3,
        strategy_variations=["aggressive", "extended_patterns", "broader_search"],
    )

    assert result == {"confidence": 0.8}
    assert best_confidence == 0.8
    assert len(attempts) == 3
