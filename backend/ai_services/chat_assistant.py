"""Transform Assistant.

Performs real, deterministic edits on the current output so the assistant works
without an external LLM provider. When a provider is configured, it is used first
and this module acts as the grounded fallback.
"""
import json
import re

from . import content_builders
from .provider import ai_provider

JARGON = content_builders.JARGON

AUDIENCE_ALIASES = {
    "school student": "School Student", "school": "School Student", "kids": "School Student",
    "college student": "College Student", "college": "College Student", "university": "College Student", "student": "College Student",
    "developer": "Developer", "engineer": "Developer", "coding": "Developer",
    "researcher": "Researcher", "academic": "Researcher",
    "business executive": "Business Executive", "executive": "Business Executive", "business": "Business Executive", "ceo": "Business Executive",
    "customer": "Customer", "client": "Customer",
    "general public": "General Public", "public": "General Public",
    "technical audience": "Technical Audience", "technical": "Technical Audience",
}

TONE_ALIASES = {
    "professional": "Professional", "formal": "Professional",
    "educational": "Educational", "teach": "Educational",
    "conversational": "Conversational", "casual": "Conversational", "friendly": "Conversational",
    "technical": "Technical",
    "persuasive": "Persuasive", "convincing": "Persuasive",
    "storytelling": "Storytelling", "story": "Storytelling",
    "simple": "Simple", "plain": "Simple",
}

DEFAULT_SUGGESTIONS = [
    "Make this simpler",
    "Create a stronger hook",
    "Remove technical jargon",
    "Make this suitable for LinkedIn",
    "Create a 30-second version",
    "Turn this into a presentation",
    "Add the key statistics",
    "Where did this statement come from?",
]


def _detect(message):
    text = message.lower()
    if any(k in text for k in ("where", "came from", "source", "evidence", "prove", "trace")):
        return "show_source"
    if "explain" in text and "claim" in text:
        return "explain_claim"
    if any(k in text for k in ("simpl", "easier", "plain english", "dumb it down", "beginner")):
        return "simplify"
    if any(k in text for k in ("jargon", "technical terms", "remove technical", "less technical")):
        return "remove_jargon"
    if any(k in text for k in ("hook", "opening", "first line", "attention", "stronger start")):
        return "hook"
    if any(k in text for k in ("30 second", "30-second", "shorter", "condense", "shorten", "brief")):
        return "shorten"
    if any(k in text for k in ("expand", "longer", "more detail", "elaborate")):
        return "expand"
    if any(k in text for k in ("presentation", "slides", "deck", "powerpoint")):
        return "presentation"
    if any(k in text for k in ("stat", "number", "data", "metric")):
        return "statistics"
    if any(k in text for k in ("bullet", "list", "bullets")):
        return "bullets"
    if any(k in text for k in ("cta", "call to action", "closing")):
        return "cta"
    if any(k in text for k in ("summary", "tl;dr", "summarize", "summarise")):
        return "summary"
    if "linkedin" in text:
        return "linkedin"
    if any(k in text for k in ("faq", "questions")):
        return "faq"
    return "adapt"


def _match(mapping, text, default=None):
    for key, value in mapping.items():
        if key in text:
            return value
    return default


def _simplify(text):
    out = text
    for term, plain in JARGON.items():
        out = re.sub(rf"\b{re.escape(term)}\b", plain, out, flags=re.IGNORECASE)
    lines = []
    for line in out.split("\n"):
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        # shorten overly long sentences
        parts = re.split(r"(?<=[.!?])\s+", stripped)
        new_parts = []
        for part in parts:
            if len(part.split()) > 26 and ", and " in part:
                new_parts.append(part.replace(", and ", ". And ", 1))
            else:
                new_parts.append(part)
        lines.append(" ".join(new_parts))
    return "\n".join(lines)


def _remove_jargon(text):
    out = text
    for term, plain in JARGON.items():
        out = re.sub(rf"\b{re.escape(term)}\b", plain, out, flags=re.IGNORECASE)
    return out


def _top_stat(dna):
    stats = (dna or {}).get("statistics") or []
    if stats:
        first = stats[0]
        return first.split(" - ", 1)[0] if " - " in first else first
    facts = (dna or {}).get("key_facts") or []
    return facts[0] if facts else ""


def _hook(text, dna):
    topic = (dna or {}).get("core_topic") or "this topic"
    stat = _top_stat(dna)
    hook = f"What if one document could change how you understand {topic.lower()}?"
    if stat:
        second = f"{stat} — and that is only one of the findings."
    else:
        second = "The evidence is more concrete than the headlines suggest."
    remaining = "\n".join(line for line in text.split("\n") if line.strip())
    return f"{hook}\n\n{second}\n\n{remaining}"


def _shorten(text):
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) <= 4:
        body = lines
    else:
        keep = max(4, round(len(lines) * 0.45))
        body = lines[:keep]
    return "\n".join(body) + "\n\nCTA: Follow for more source-grounded breakdowns."


def _expand(text, dna, claims):
    facts = (dna or {}).get("key_facts") or []
    stats = (dna or {}).get("statistics") or []
    args = (dna or {}).get("key_arguments") or []
    extra = ["\n\n## Additional Evidence\n"]
    extra += [f"• {s}" for s in stats[:5]]
    extra += [f"• {f}" for f in facts[:5]]
    if args:
        extra.append("\n## Supporting Arguments\n")
        extra += [f"{i + 1}. {a}" for i, a in enumerate(args[:4])]
    return text + "\n".join(extra)


def _presentation(text, dna):
    topic = (dna or {}).get("core_topic") or "Overview"
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    slides = [f"SLIDE 1 — TITLE\n{topic}\nSPEAKER NOTE: State the thesis in one sentence."]
    for i, block in enumerate(blocks[:7], start=2):
        first = block.split("\n")[0][:70]
        slides.append(f"SLIDE {i} — {first}\n{block[:400]}\nSPEAKER NOTE: Expand this point verbally.")
    return "\n\n".join(slides)


def _statistics(text, dna):
    stats = (dna or {}).get("statistics") or []
    if not stats:
        return text
    block = "## By the Numbers\n" + "\n".join(f"• {s}" for s in stats[:8])
    return f"{text}\n\n{block}"


def _bullets(text):
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    out = []
    for line in lines:
        if line.startswith("#") or line.startswith("•") or line.startswith("["):
            out.append(line)
        else:
            out.append(f"• {line}")
    return "\n".join(out)


def _cta(text, audience):
    closers = {
        "Business Executive": "CTA: Book a strategic walkthrough of this analysis.",
        "College Student": "CTA: Follow for more breakdowns you can use in your studies.",
        "Developer": "CTA: Try the API and inspect the claim ledger yourself.",
        "Researcher": "CTA: Request the full source and methodology notes.",
    }
    return f"{text}\n\n{closers.get(audience, 'CTA: Follow for more source-grounded analysis.')}"


def _summary(text, dna):
    facts = (dna or {}).get("key_facts") or []
    args = (dna or {}).get("key_arguments") or []
    topic = (dna or {}).get("core_topic") or "This source"
    return (
        f"TL;DR — {topic}\n\n"
        f"{' '.join(facts[:2])}\n\n"
        f"Key arguments: {len(args)}.\n\n"
        f"{args[0] if args else ''}"
    ).strip()


def _linkedin(text, dna):
    keywords = (dna or {}).get("important_keywords") or []
    tags = " ".join("#" + k.replace(" ", "").replace("-", "") for k in keywords[:5])
    return f"Here is what the source actually establishes:\n\n{text}\n\nWhat is your take? 👇\n\n{tags}"


def _faq(text, dna, claims):
    facts = (dna or {}).get("key_facts") or []
    faqs = [f"Q: What is the core topic?\nA: {(dna or {}).get('core_topic', 'See source')}"]
    for fact in facts[:6]:
        question = fact.split(" ")[:8]
        faqs.append(f"Q: What does the source say about {' '.join(question).rstrip('.,')}?\nA: {fact}")
    return "\n\n".join(faqs)


def _best_claim(text, claims):
    claims = claims or []
    if not claims:
        return None
    lower = text.lower()
    best, best_score = None, 0
    for claim in claims:
        words = [w for w in re.findall(r"[a-z]{4,}", (claim.get("claim_text") or "").lower())]
        if not words:
            continue
        score = sum(1 for w in words if w in lower)
        if score > best_score:
            best, best_score = claim, score
    return best or claims[0]


async def chat_assistant(message, current_output, source_text, context=None):
    context = context or {}
    dna = context.get("dna") or {}
    claims = context.get("claims") or []
    output_format = context.get("output_format")
    audience = context.get("audience") or "General Public"
    level = context.get("knowledge_level") or "Intermediate"
    tone = context.get("tone") or "Professional"

    if ai_provider.demo_mode:
        action = _detect(message)
        lower = message.lower()

        # Informational intents do not modify the content.
        if action == "show_source":
            claim = _best_claim(current_output, claims)
            if claim:
                return {
                    "response": (
                        f"That statement traces back to {claim.get('source_location') or 'the source document'} "
                        f"with {round(claim.get('confidence', 0) * 100)}% confidence.\n\n"
                        f"Source text: “{claim.get('supporting_source_text')}”"
                    ),
                    "action": "show_source",
                    "modified_content": None,
                    "highlight_claim": claim.get("claim_text"),
                    "suggested_actions": DEFAULT_SUGGESTIONS,
                }
            return {"response": "I could not find a matching source claim. Run the source analysis again to rebuild the claim ledger.",
                    "action": "show_source", "modified_content": None, "suggested_actions": DEFAULT_SUGGESTIONS}

        if action == "explain_claim":
            claim = _best_claim(current_output, claims)
            if claim:
                return {
                    "response": (
                        f"Here is the claim and its support:\n\n"
                        f"Claim: {claim.get('claim_text')}\n"
                        f"Evidence: “{claim.get('supporting_source_text')}”\n"
                        f"Location: {claim.get('source_location')}\n"
                        f"Confidence: {round(claim.get('confidence', 0) * 100)}%"
                    ),
                    "action": "explain_claim",
                    "modified_content": None,
                    "highlight_claim": claim.get("claim_text"),
                    "suggested_actions": DEFAULT_SUGGESTIONS,
                }

        # Audience / tone switching rebuilds the output in the right voice.
        new_audience = _match(AUDIENCE_ALIASES, lower)
        new_tone = _match(TONE_ALIASES, lower) if action == "adapt" else None
        if action == "adapt" and (new_audience or new_tone) and output_format:
            content = content_builders.build_format_content(
                output_format,
                new_audience or audience,
                level,
                new_tone or tone,
                dna,
                claims,
                source_text,
            )["content"]
            target = new_audience or audience
            return {
                "response": f"Rewritten for a {target} audience with a {new_tone or tone} tone. Facts are unchanged.",
                "action": "adapt",
                "modified_content": content,
                "new_audience": new_audience,
                "new_tone": new_tone,
                "suggested_actions": DEFAULT_SUGGESTIONS,
            }

        if not current_output.strip():
            return {
                "response": "Generate an output first, then I can edit it. Try the Transform button in the Studio.",
                "action": "noop",
                "modified_content": None,
                "suggested_actions": DEFAULT_SUGGESTIONS,
            }

        if action == "simplify":
            new_content, note = _simplify(current_output), "Simplified the language and shortened long sentences."
        elif action == "remove_jargon":
            new_content, note = _remove_jargon(current_output), "Replaced technical terms with plain equivalents."
        elif action == "hook":
            new_content, note = _hook(current_output, dna), "Added a stronger opening hook drawn from the source."
        elif action == "shorten":
            new_content, note = _shorten(current_output), "Condensed the output and kept the closing call to action."
        elif action == "expand":
            new_content, note = _expand(current_output, dna, claims), "Expanded with additional source evidence."
        elif action == "presentation":
            new_content, note = _presentation(current_output, dna), "Converted the output into a slide deck outline."
        elif action == "statistics":
            new_content, note = _statistics(current_output, dna), "Added the key statistics from the source."
        elif action == "bullets":
            new_content, note = _bullets(current_output), "Converted the content into bullets."
        elif action == "cta":
            new_content, note = _cta(current_output, audience), f"Added a call to action suited to a {audience} audience."
        elif action == "summary":
            new_content, note = _summary(current_output, dna), "Produced a concise summary."
        elif action == "linkedin":
            new_content, note = _linkedin(current_output, dna), "Reformatted for LinkedIn with hashtags."
        elif action == "faq":
            new_content, note = _faq(current_output, dna, claims), "Converted the content into an FAQ."
        else:
            new_content, note = _simplify(current_output), "Applied a general clarity pass."

        return {
            "response": f"{note} The source facts are unchanged.",
            "action": action,
            "modified_content": new_content,
            "suggested_actions": DEFAULT_SUGGESTIONS,
        }

    prompt = f"""You are the TransformIQ assistant. Edit the current output based on the user request.

Current output:
{current_output[:3000]}

Source DNA: {json.dumps(dna)[:1500]}
Claims: {json.dumps(claims[:10])[:1500]}
Format: {output_format} | Audience: {audience} | Level: {level} | Tone: {tone}

User request: {message}

Return ONLY valid JSON with keys: response (string), modified_content (string or null),
action (string), suggested_actions (array of strings). Never invent facts not present in the claims."""

    system = "You are a precise content editing assistant. Preserve factual meaning."
    result = await ai_provider.generate(prompt, system)
    try:
        parsed = json.loads(result)
        if not isinstance(parsed, dict) or not parsed.get("response"):
            ai_provider.demo_mode = True
            return await chat_assistant(message, current_output, source_text, context)
        parsed.setdefault("suggested_actions", DEFAULT_SUGGESTIONS)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return {
            "response": result,
            "modified_content": None,
            "action": "unknown",
            "suggested_actions": DEFAULT_SUGGESTIONS,
        }
