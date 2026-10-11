"""Claim extractor service."""
from . import demo_data, text_analysis
from .provider import ai_provider


async def extract_claims(raw_text):
    if ai_provider.demo_mode:
        if demo_data.is_sample_document(raw_text):
            return demo_data.generate_demo_claims(raw_text)
        return text_analysis.extract_text_claims(raw_text)

    prompt = f"""Extract all important factual claims from the following content. For each claim, provide:
- claim_text: The factual statement
- supporting_source_text: The exact text from the source that supports this claim
- source_location: Where in the document this appears
- importance: high/medium/low
- confidence: 0.0-1.0

Return a JSON array of claims. Focus on verifiable facts, statistics, and data-driven statements.

CONTENT:
{raw_text[:4000]}

Return ONLY valid JSON array, no other text."""

    system = "You are an expert fact extractor. Identify all verifiable claims in content."
    result = await ai_provider.generate(prompt, system)
    try:
        import json
        parsed = json.loads(result)
        if not isinstance(parsed, list) or not all(isinstance(item, dict) and item.get("claim_text") for item in parsed):
            raise ValueError("Provider returned an invalid claims array")
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        return demo_data.generate_demo_claims(raw_text) if demo_data.is_sample_document(raw_text) else text_analysis.extract_text_claims(raw_text)
