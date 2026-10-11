"""Transformation engine service."""
import json
import re
from pydantic import BaseModel, Field, ValidationError
from . import demo_data
from .provider import ai_provider
from . import storyboard_generator


class GeneratedContentResponse(BaseModel):
    content: str = Field(min_length=1)
    trace: list[dict] = Field(default_factory=list)


def retrieve_relevant_context(source_text, claims, dna, max_chars=7000):
    """Select source paragraphs relevant to the requested transformation.

    This is a deterministic retrieval layer for long documents. It keeps high-
    importance claims and ranks paragraphs by topic/keyword/claim overlap, then
    returns them in original document order.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", source_text or "") if p.strip()]
    if not paragraphs:
        return source_text[:max_chars]
    query = set(re.findall(r"[a-z0-9%$]{2,}", " ".join([
        dna.get("core_topic", ""), " ".join(dna.get("important_keywords", []) or []),
        " ".join(c.get("claim_text", "") for c in claims[:12]),
    ]).lower()))
    ranked = []
    for index, paragraph in enumerate(paragraphs):
        tokens = set(re.findall(r"[a-z0-9%$]{2,}", paragraph.lower()))
        score = len(tokens & query)
        if re.search(r"\d", paragraph):
            score += 2
        ranked.append((score, index, paragraph))
    selected = []
    total = 0
    for score, index, paragraph in sorted(ranked, key=lambda item: (-item[0], item[1])):
        if not score and selected:
            continue
        if total + len(paragraph) > max_chars:
            continue
        selected.append((index, paragraph))
        total += len(paragraph) + 2
    selected.sort(key=lambda item: item[0])
    return "\n\n".join(paragraph for _, paragraph in selected)[:max_chars] or source_text[:max_chars]


async def create_transformation_plan(source_text, output_format, audience, knowledge_level, tone):
    strategy = demo_data.TRANSFORMATION_STRATEGIES.get(output_format, {})
    quotas = {
        "30-second Reel Script": 2, "60-second Reel Script": 4, "Social Media Post": 2,
        "X/Twitter Thread": 5, "Executive Summary": 6, "Press Release": 5,
    }
    plan = {
        "output_format": output_format,
        "audience": audience,
        "knowledge_level": knowledge_level,
        "tone": tone,
        "structure": strategy.get("structure", "Introduction → Body → Conclusion"),
        "target_length": strategy.get("length", "Variable"),
        "approach": strategy.get("approach", "Adapt content for the target audience and format"),
        "claim_quota": quotas.get(output_format, 5),
        "audience_rule": (
            "Lead with business impact, cost, and risk; keep recommendations explicit."
            if audience == "Business Executive" else
            "Define every term, use one concrete analogy, keep sentences under 22 words."
            if knowledge_level == "Beginner" or audience == "School Student" else
            "Preserve technical terms and evidence density; name limitations."
            if knowledge_level == "Expert" or audience in ("Developer", "Technical Audience", "Researcher") else
            "Balance accessibility with evidence; explain why each fact matters to this audience."
        ),
        "steps": [
            {"step": 1, "action": f"Select the {quotas.get(output_format, 5)} source claims most relevant to a {audience} audience"},
            {"step": 2, "action": f"Rewrite at {knowledge_level} level without changing any number, entity, or causal claim"},
            {"step": 3, "action": f"Apply {tone} tone and the {output_format} structure"},
            {"step": 4, "action": "Generate the output using only selected claims plus explicitly-marked framing"},
            {"step": 5, "action": "Verify every factual sentence against the claim ledger; flag the rest as unsupported"},
            {"step": 6, "action": "Score coverage, consistency, audience fit, and readability"},
        ],
    }
    if ai_provider.demo_mode:
        return plan

    relevant_context = retrieve_relevant_context(source_text, [], {}, max_chars=4000)
    prompt = f"""You are a content strategist. Plan how to transform a source into {output_format}.

STAGE 1 — OBJECTIVE: state the single job this output must do for a {audience} audience ({knowledge_level} level).
STAGE 2 — CLAIM SELECTION: from the source claims below, pick the {plan['claim_quota']} most relevant and quote each claim text verbatim.
STAGE 3 — STRUCTURE: map each selected claim to a section of this structure: {plan['structure']}.
STAGE 4 — AUDIENCE RULE: {plan['audience_rule']}
STAGE 5 — GROUNDING RULES: never invent numbers, names, dates, or causal claims; mark any connective framing as framing.

Relevant source passages (retrieved in document order):
{relevant_context}
Tone: {tone}

Return ONLY valid JSON with keys: objective, selected_claims (array of verbatim claim strings),
section_map (array of {{section, claim}}), audience_rule, grounding_notes."""

    system = "You are an expert content strategist. Create detailed transformation plans."
    result = await ai_provider.generate(prompt, system)
    try:
        parsed = json.loads(result)
        return {
            **plan,
            "objective": parsed.get("objective", plan["audience_rule"]),
            "selected_claims": parsed.get("selected_claims", []),
            "section_map": parsed.get("section_map", []),
            "grounding_notes": parsed.get("grounding_notes", "Claims must remain traceable to the source."),
        }
    except json.JSONDecodeError:
        strategy = demo_data.TRANSFORMATION_STRATEGIES.get(output_format, {})
        return {"output_format": output_format, "structure": strategy.get("structure", ""), "approach": strategy.get("approach", "")}


async def generate_output(source_text, claims, dna, output_format, audience, knowledge_level, tone, requested_length="medium"):
    demo_result = demo_data.generate_demo_transformation(output_format, audience, knowledge_level, tone, source_text, claims, dna, requested_length)

    if ai_provider.demo_mode:
        return demo_result

    claims_text = "\n".join([f"- {c['claim_text']}" for c in claims[:10]])
    dna_text = f"Core Topic: {dna.get('core_topic', 'N/A')}\nSummary: {dna.get('summary', 'N/A')}"
    relevant_context = retrieve_relevant_context(source_text, claims, dna)

    prompt = f"""Transform source content into a {output_format} by running these stages in order:

STAGE 1 — OBJECTIVE: one sentence stating what a {audience} reader ({knowledge_level} level) must take away.
STAGE 2 — EVIDENCE: use ONLY these source claims; quote numbers, names, and dates verbatim; never invent new ones:
{claims_text}

SOURCE DNA:
{dna_text}

STAGE 3 — AUDIENCE TRANSLATION:
- School Student / Beginner: define every term, use one concrete analogy (e.g. explain a technical process the way you would explain a familiar everyday system), sentences under 22 words.
- College Student: connect each fact to studies or career relevance.
- Developer / Technical Audience / Expert: keep precise terms, name the mechanism and the failure mode.
- Researcher: cite the evidence, note limitations.
- Business Executive: lead with cost, market movement, and risk; end with a recommendation.
STAGE 4 — STRUCTURE: follow the {output_format} structure exactly.
STAGE 5 — TONE: {tone} throughout.
STAGE 5B — LENGTH: target a {requested_length} output; do not remove a number or qualification just to shorten it.
STAGE 6 — SELF-CHECK: list every factual sentence in your draft; if any cannot be traced to a claim above, either remove it or mark it [UNVERIFIED].

RETRIEVED SOURCE PASSAGES:
{relevant_context}

Return ONLY valid JSON with keys "content" (the finished {output_format}) and "trace" (array of {{sentence, claim_or_UNVERIFIED}}). No other text."""

    system = f"You are an expert content creator specializing in {output_format} content."
    result = await ai_provider.generate(prompt, system)
    try:
        parsed = GeneratedContentResponse.model_validate(json.loads(result))
        content = parsed.content
        is_video = "reel" in output_format.lower() or "youtube" in output_format.lower()
        storyboard = await storyboard_generator.generate_storyboard(content, output_format, audience, tone) if is_video else None
        word_count = len(content.split())
        return {
            "content": content,
            "estimated_length": f"{word_count} words",
            "storyboard": storyboard,
            "verification": parsed.trace,
        }
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return demo_result


async def generate_variations(source_text, claims, dna, output_format, audience, knowledge_level, tone):
    """Three genuinely different, all-grounded variants: Safe, Engaging, Creative."""
    from . import content_builders

    bank = content_builders._fact_bank(dna, claims, source_text)
    stats = bank["statistics"][:3]
    args = bank["arguments"][:3]
    topic = bank["topic"]
    base = demo_data.generate_demo_transformation(output_format, audience, knowledge_level, tone, source_text, claims, dna)

    factual = dict(base)
    factual["variation_type"] = "factual"
    factual["content"] = (
        f"{topic}: what the source establishes\n\n"
        + "\n".join(f"• {s}" for s in stats + args[:2])
        + f"\n\nSource: {len(claims)} extracted claims. No framing added."
    )

    engaging = dict(base)
    engaging["variation_type"] = "engaging"
    engaging["content"] = (
        f"{topic} — the version worth sharing\n\n"
        f"{stats[0] if stats else args[0] if args else topic}\n\n"
        "Why it matters: " + (args[0] if args else topic) + "\n\n"
        + "\n".join(f"→ {s}" for s in (stats[1:] + args[1:])[:3])
        + "\n\nYour move: share the one number that surprised you. 👇"
    )

    creative = dict(base)
    creative["variation_type"] = "creative"
    creative["content"] = (
        f"A short story the data tells about {topic.lower()}\n\n"
        f"It began with a measurement: {stats[0] if stats else args[0] if args else 'a documented effect'}\n\n"
        "Then came the pattern: " + (args[0] if args else topic) + "\n\n"
        "And the honest ending: " + ((bank["conclusions"] or ["implementation decides the outcome"])[0]) + "\n\n"
        "All three beats come straight from the source ledger."
    )
    return [factual, engaging, creative]
