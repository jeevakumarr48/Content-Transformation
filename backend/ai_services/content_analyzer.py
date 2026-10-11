"""Content DNA analyzer service."""
from . import demo_data, text_analysis
from .provider import ai_provider


async def analyze_content(raw_text):
    if ai_provider.demo_mode:
        if demo_data.is_sample_document(raw_text):
            return demo_data.generate_demo_content_dna(raw_text)
        return text_analysis.analyze_text(raw_text)

    prompt = f"""Analyze the following content and extract its Content DNA. Return a JSON object with these fields:
- core_topic: The main subject (1 line)
- summary: 2-3 sentence summary
- main_objective: What the content aims to achieve
- key_arguments: Array of main arguments/claims (3-6 items)
- key_facts: Array of important facts (5-8 items)
- statistics: Array of key statistics mentioned (3-6 items)
- important_entities: Array of people, organizations, places mentioned
- important_keywords: Array of key terms (8-12 items)
- key_quotes: Array of notable quotes
- conclusions: Array of main conclusions
- target_audiences: Array of who would benefit from this content
- tone: Overall tone of the content
- complexity_level: Beginner/Intermediate/Advanced
- estimated_reading_time: How long to read
- content_category: Type of content (Article, Report, etc.)

CONTENT:
{raw_text[:4000]}

Return ONLY valid JSON, no other text."""

    system = "You are an expert content analyst. Analyze content thoroughly and return structured JSON data."
    result = await ai_provider.generate(prompt, system)
    try:
        import json
        parsed = json.loads(result)
        if not isinstance(parsed, dict) or not parsed.get("core_topic"):
            raise ValueError("Provider returned an invalid Content DNA object")
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        return demo_data.generate_demo_content_dna(raw_text) if demo_data.is_sample_document(raw_text) else text_analysis.analyze_text(raw_text)
