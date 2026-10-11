"""Knowledge mapper service."""
from . import demo_data, text_analysis
from .provider import ai_provider


async def build_knowledge_map(raw_text):
    if ai_provider.demo_mode:
        if demo_data.is_sample_document(raw_text):
            return demo_data.generate_demo_knowledge_nodes(raw_text)
        return text_analysis.build_text_map(raw_text)

    prompt = f"""Create a knowledge map for the following content. Return a JSON array of nodes.
Each node should have:
- node_type: topic/concept/argument/evidence/example/challenge/conclusion
- label: Short label (2-5 words)
- content: Brief description
- parent_id: ID of parent node (null for root)
- source_text: Supporting text from the original

Create 12-15 interconnected nodes.

CONTENT:
{raw_text[:4000]}

Return ONLY valid JSON array, no other text."""

    system = "You are an expert knowledge architect. Create clear, interconnected knowledge structures."
    result = await ai_provider.generate(prompt, system)
    try:
        import json
        parsed = json.loads(result)
        if not isinstance(parsed, list) or not all(isinstance(item, dict) and item.get("label") for item in parsed):
            raise ValueError("Provider returned an invalid knowledge map")
        return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        return demo_data.generate_demo_knowledge_nodes(raw_text) if demo_data.is_sample_document(raw_text) else text_analysis.build_text_map(raw_text)
