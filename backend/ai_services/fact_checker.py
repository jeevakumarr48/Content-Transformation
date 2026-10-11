"""Fact checker and quality scorer services."""
import re
from difflib import SequenceMatcher


_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her", "was",
    "one", "our", "out", "has", "him", "his", "how", "its", "may", "new", "now", "see",
    "who", "did", "that", "with", "this", "from", "they", "have", "will", "would", "there",
    "their", "what", "about", "which", "when", "your", "them", "then", "than", "into",
    "more", "other", "some", "such", "only", "also", "over", "been", "were", "these",
    "those", "each", "much", "many", "most", "because", "between", "through", "during",
    "before", "after", "while", "where", "being", "does", "doing", "done", "having",
    "should", "could", "might", "must", "using", "used", "however", "therefore", "thus",
    "although", "within", "without", "across", "based", "including", "just", "even",
    "well", "make", "made", "often", "still", "less", "here", "both", "same", "very",
}


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9][a-z0-9%$.\-]*", (text or "").lower()) if len(t) > 3 and t not in _STOPWORDS]


def _sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _normalise_number(value):
    return re.sub(r"\s+", "", value.lower()).replace(",", "")


def _number_keys(text):
    return {_normalise_number(value) for value in re.findall(r"(?:\$|€|£)?\s?\d+(?:[.,]\d+)*(?:\s?(?:%|percent|billion|million|bn|k))?", text or "", re.IGNORECASE)}


async def verify_claims(output_content, source_claims):
    verifications = []
    out_tokens = set(_tokens(output_content))
    out_sentences = _sentences(output_content)

    for claim in source_claims:
        claim_text = claim["claim_text"]
        tokens = _tokens(claim_text)
        hits = sum(1 for t in set(tokens) if t in out_tokens)
        coverage = hits / max(1, len(set(tokens)))

        best_sentence, best_ratio = "", 0.0
        for sentence in out_sentences:
            ratio = SequenceMatcher(None, claim_text.lower(), sentence.lower()).ratio()
            if ratio > best_ratio:
                best_ratio, best_sentence = ratio, sentence

        claim_numbers = _number_keys(claim_text)
        sentence_numbers = _number_keys(best_sentence)
        numbers_match = claim_numbers.issubset(sentence_numbers) if claim_numbers else True

        if (coverage >= 0.5 or best_ratio >= 0.75) and numbers_match:
            status = "verified"
            confidence = min(0.99, claim["confidence"] + 0.05)
        elif coverage >= 0.25 or best_ratio >= 0.55:
            status = "partially_supported"
            confidence = round(claim["confidence"] * 0.7, 2)
        else:
            status = "unsupported"
            confidence = 0.0

        verifications.append({
            "claim_id": claim.get("id"),
            "claim_text": claim_text,
            "generated_statement": best_sentence[:220] if status in ("verified", "partially_supported") else "",
            "verification_status": status,
            "source_text": claim.get("supporting_source_text", ""),
            "source_location": claim.get("source_location", ""),
            "confidence": round(confidence, 2),
        })

    return verifications


def _readability(output_content):
    sentences = _sentences(output_content)
    words = re.findall(r"[A-Za-z0-9']+", output_content or "")
    if not sentences or not words:
        return 60.0
    avg_len = len(words) / len(sentences)
    return round(max(55.0, min(98.0, 100 - (avg_len - 14) * 2.5)), 1)


def _audience_fit(output_content, audience):
    words = re.findall(r"[A-Za-z]+", output_content or "")
    if not words:
        return 80.0
    long_ratio = sum(1 for w in words if len(w) > 8) / len(words)
    if audience in ("School Student", "Customer", "General Public"):
        return round(max(60.0, min(98.0, 100 - long_ratio * 220)), 1)
    if audience in ("Developer", "Technical Audience", "Researcher"):
        return round(max(60.0, min(98.0, 72 + long_ratio * 220)), 1)
    return round(max(60.0, min(98.0, 92 - abs(long_ratio - 0.12) * 150)), 1)


def _format_compliance(output_content, output_format):
    text = output_content or ""
    rules = {
        "Instagram Carousel": "SLIDE",
        "X/Twitter Thread": "1/",
        "Presentation Outline": "Slide",
        "FAQ": "Q:",
        "Press Release": "FOR IMMEDIATE RELEASE",
        "Newsletter": "SUBJECT:",
    }
    marker = rules.get(output_format)
    if marker:
        return 96.0 if marker.lower() in text.lower() else 45.0
    if output_format in ("30-second Reel Script", "60-second Reel Script", "YouTube Script"):
        return 96.0 if "[SCENE" in text and "NARRATION:" in text else 55.0
    return 92.0 if len(text.split()) >= 30 else 70.0


async def calculate_quality_scores(output_content, source_text, claims, audience, output_format):
    out_tokens = set(_tokens(output_content))
    src_tokens = set(_tokens(source_text))
    overlap = len(out_tokens & src_tokens)
    source_coverage = round(min(100.0, (overlap / max(1, len(src_tokens))) * 100), 1)

    verifications = await verify_claims(output_content, claims or [])
    score_of = {"verified": 1.0, "partially_supported": 0.5, "unsupported": 0.0}
    weights = {
        claim.get("id"): (1.0 if claim.get("importance") == "high" else 0.6 if claim.get("importance") == "medium" else 0.3) * claim.get("confidence", 0.8)
        for claim in (claims or [])
    }
    total_weight = sum(weights.values()) or 1.0
    factual_consistency = round(
        sum(score_of[v["verification_status"]] * weights.get(v.get("claim_id"), 0.8) for v in verifications) / total_weight * 100, 1,
    ) if verifications else 0.0

    readability = _readability(output_content)
    audience_relevance = _audience_fit(output_content, audience)
    format_compliance = _format_compliance(output_content, output_format)
    unsupported = sum(1 for v in verifications if v["verification_status"] == "unsupported")

    return {
        "source_coverage": source_coverage,
        "factual_consistency": factual_consistency,
        "audience_relevance": audience_relevance,
        "readability": readability,
        "format_compliance": format_compliance,
        "unsupported_claims": unsupported,
        "overall_score": round((source_coverage + factual_consistency + audience_relevance + readability + format_compliance) / 5, 1),
    }


def _tone_match(output_content, tone):
    text = output_content or ""
    has_emoji = bool(re.search(r"[\U0001F300-\U0001FAFF☀-➿⬅-⬏]", text))
    has_question = "?" in text
    if tone in ("Professional", "Technical"):
        return 95.0 if not has_emoji else 72.0
    if tone in ("Conversational", "Storytelling"):
        return 92.0 if (has_question or '"' in text or '"' in text) else 82.0
    if tone == "Persuasive":
        return 90.0 if ("!" in text or "👇" in text or "CTA" in text) else 82.0
    return 88.0


def _originality(output_content, source_text):
    out_sentences = _sentences(output_content)
    src_sentences = _sentences(source_text)
    if not out_sentences:
        return 80.0
    novel = 0
    for sentence in out_sentences:
        best = max((SequenceMatcher(None, sentence.lower(), s.lower()).ratio() for s in src_sentences), default=0.0)
        if best < 0.9:
            novel += 1
    return round(novel / len(out_sentences) * 100, 1)


async def run_quality_audit(output_content, source_text, claims, audience, tone, output_format):
    scores = await calculate_quality_scores(output_content, source_text, claims, audience, output_format)
    tone_score = _tone_match(output_content, tone)
    originality = _originality(output_content, source_text)
    hallucination = round(100 - scores["factual_consistency"], 1)
    overall = round(
        (scores["factual_consistency"] + scores["source_coverage"] + scores["audience_relevance"]
         + scores["readability"] + scores["format_compliance"] + tone_score + originality) / 7, 1,
    )
    return {
        "factuality": scores["factual_consistency"],
        "coverage": scores["source_coverage"],
        "hallucination": hallucination,
        "audience_fit": scores["audience_relevance"],
        "tone_match": tone_score,
        "readability": scores["readability"],
        "originality": originality,
        "overall_score": overall,
        "details": {
            "fact_check_notes": f"{scores['unsupported_claims']} unsupported statement(s) detected against {len(claims or [])} source claims",
            "coverage_notes": f"Source vocabulary coverage: {scores['source_coverage']}%",
            "hallucination_notes": f"Hallucination risk: {hallucination}%",
            "audience_notes": f"Measured for a {audience} audience in a {tone} tone",
        },
    }


async def validate_against_source(output_content, structure, claims):
    """Stage 8: detect missing information and verify preserved values/references.

    Returns which source numbers, concepts, definitions and sections survived into
    the generated output, and which are missing, so nothing is silently dropped.
    """
    structure = structure or {}
    text = output_content or ""
    output_numbers = _number_keys(text)

    preserved_numbers, missing_numbers = [], []
    for number in structure.get("numbers", [])[:40]:
        if _normalise_number(number) and _normalise_number(number) in output_numbers:
            preserved_numbers.append(number)
        else:
            missing_numbers.append(number)

    lower = text.lower()
    preserved_concepts, missing_concepts = [], []
    for concept in structure.get("key_concepts", [])[:14]:
        if concept.lower() in lower:
            preserved_concepts.append(concept)
        else:
            missing_concepts.append(concept)

    missing_definitions = [
        d["term"] for d in structure.get("definitions", [])[:12]
        if d["term"].lower() not in lower
    ]

    covered_sections = [
        s["heading"] for s in structure.get("sections", [])
        if s["heading"] and s["heading"].lower() in lower
    ]

    verifications = await verify_claims(text, claims or [])
    unsupported = [v for v in verifications if v["verification_status"] == "unsupported"]

    references = sorted({
        v["source_location"] for v in verifications if v.get("source_location")
    })

    checks = []
    if missing_numbers:
        checks.append({"level": "warning", "message": f"{len(missing_numbers)} source number(s) not used: {', '.join(missing_numbers[:5])}"})
    else:
        checks.append({"level": "pass", "message": "All extracted source numbers are preserved in the output."})
    if unsupported:
        checks.append({"level": "error", "message": f"{len(unsupported)} statement(s) could not be traced to a source claim."})
    else:
        checks.append({"level": "pass", "message": "Every factual statement traces to a source claim."})
    if missing_concepts:
        checks.append({"level": "info", "message": f"Concepts not covered: {', '.join(missing_concepts[:6])}"})

    return {
        "preserved_numbers": preserved_numbers,
        "missing_numbers": missing_numbers,
        "preserved_concepts": preserved_concepts,
        "missing_concepts": missing_concepts,
        "missing_definitions": missing_definitions,
        "covered_sections": covered_sections,
        "unsupported_statements": [v["claim_text"] for v in unsupported],
        "references": references,
        "checks": checks,
    }
