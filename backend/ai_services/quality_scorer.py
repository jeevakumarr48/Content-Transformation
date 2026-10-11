"""Quality scoring facade used by API consumers that need a named service."""

from .fact_checker import calculate_quality_scores, run_quality_audit

__all__ = ["calculate_quality_scores", "run_quality_audit"]
