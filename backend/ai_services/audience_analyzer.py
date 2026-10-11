"""Audience intelligence kept separate so audience strategy can evolve independently."""


def select_relevant_claims(claims, audience: str, knowledge_level: str):
    if not claims:
        return []
    high_priority = [claim for claim in claims if claim.get("importance") == "high"]
    return (high_priority or claims)[:8]
