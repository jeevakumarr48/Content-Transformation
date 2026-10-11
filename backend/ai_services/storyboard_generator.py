"""Storyboard generator for video outputs."""
from . import demo_data
from .provider import ai_provider


async def generate_storyboard(content, output_format, audience, tone):
    if ai_provider.demo_mode:
        existing = demo_data.generate_demo_transformation(
            "60-second Reel Script", audience, "Intermediate", tone, "", [], {}
        )
        if existing.get("storyboard"):
            return existing["storyboard"]

    prompt = f"""Generate a video storyboard for the following content.
Target: {audience}, Tone: {tone}, Format: {output_format}

Content excerpt:
{content[:1500]}

Create a storyboard with 5-7 scenes. Each scene should have:
- scene: Scene number
- duration: Time range (e.g., "0-5s")
- visual: Visual direction/suggestion
- narration: What the narrator says
- on_screen_text: Text overlay

Return ONLY valid JSON array, no other text."""

    system = "You are an expert video producer. Create engaging storyboards."
    result = await ai_provider.generate(prompt, system)
    try:
        import json
        return json.loads(result)
    except json.JSONDecodeError:
        return [
            {"scene": 1, "duration": "0-5s", "visual": "Opening shot", "narration": "Introduction", "on_screen_text": "Title"},
            {"scene": 2, "duration": "5-15s", "visual": "Main content visual", "narration": content[:100], "on_screen_text": "Key Point 1"},
            {"scene": 3, "duration": "15-30s", "visual": "Supporting visual", "narration": content[100:200], "on_screen_text": "Key Point 2"},
            {"scene": 4, "duration": "30-45s", "visual": "Data visualization", "narration": content[200:300], "on_screen_text": "Key Point 3"},
            {"scene": 5, "duration": "45-60s", "visual": "Closing shot", "narration": "Conclusion and CTA", "on_screen_text": "Follow for more"},
        ]
