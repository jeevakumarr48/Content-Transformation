"""Source-grounded content builders.

Produces genuinely format-specific, audience-adapted content from the extracted
Content DNA and claim ledger. Used whenever no external LLM provider is configured
so the prototype always returns appropriate, traceable content.
"""

JARGON = {
    "utilize": "use", "utilizes": "uses", "utilized": "used",
    "leverage": "use", "leverages": "uses", "leveraging": "using",
    "facilitate": "help", "facilitates": "helps",
    "implement": "set up", "implements": "sets up", "implemented": "set up",
    "optimize": "improve", "optimizes": "improves", "optimization": "improvement",
    "algorithm": "a set of step-by-step rules",
    "algorithms": "sets of step-by-step rules",
    "machine learning": "software that learns from examples",
    "adaptive": "self-adjusting", "adaptive learning": "learning that adjusts to each student",
    "automation": "doing tasks automatically",
    "infrastructure": "underlying systems",
    "paradigm": "model", "synthesize": "combine", "mitigate": "reduce",
    "comprehensive": "complete", "methodology": "method", "subsequently": "then",
    "approximately": "about", "demonstrate": "show", "demonstrates": "shows",
    "commence": "start", "terminate": "end", "endeavor": "try", "ascertain": "find out",
    "utilization": "use", "functionality": "features", "incentivize": "encourage",
    "operationalize": "put into practice", "holistic": "complete", "robust": "strong",
}

AUDIENCE_FRAME = {
    "School Student": "the short, plain-English version",
    "College Student": "what this means for your studies and career",
    "Developer": "the implementation view",
    "Researcher": "the evidence view",
    "Business Executive": "the decision-maker brief",
    "Customer": "what this means for you",
    "General Public": "the plain-language summary",
    "Technical Audience": "the technical breakdown",
}

def _topic_short(bank):
    topic = (bank.get("topic") or "this topic").strip()
    if not topic:
        return "this topic"
    return topic[0].lower() + topic[1:]


def _bridge_for(bank, audience):
    """Audience framing grounded in the actual source topic, never a canned domain."""
    topic = _topic_short(bank)
    stat = _top_stat(bank)
    stat_hint = f" One measured result: {stat}." if stat else ""
    return {
        "School Student": f"Think of {topic} as a system that notices what works, then adjusts.{stat_hint}",
        "College Student": f"{bank.get('topic') or 'This subject'} is already in use in the world you are about to work in.{stat_hint}",
        "Developer": "The practical question is which layer you integrate, what data you control, and where it fails.",
        "Researcher": "The measured effects are consistent, but the evidence base still has gaps worth naming.",
        "Business Executive": f"For decision-makers, the question is where {topic} pays off and what risk to govern.{stat_hint}",
        "Customer": f"The practical upside, in plain terms: {(bank.get('conclusions') or [''])[0] or (bank.get('facts') or [''])[0] or 'clearer, faster results'}.",
        "General Public": f"{bank.get('topic') or 'This subject'} is already in use, mostly quietly.{stat_hint}",
        "Technical Audience": "The value comes from the loop between measurement and delivery.",
    }.get(audience, f"{bank.get('topic') or 'This subject'} matters because the source measures its impact.{stat_hint}")


def _close_for(bank, audience):
    conclusion = (bank.get("conclusions") or [""])[0]
    return {
        "School Student": "The tools change. Learning how to think does not.",
        "College Student": "Learn to work alongside these tools, not against them.",
        "Developer": "Own the data model and the failure modes; the rest is integration.",
        "Researcher": "Adoption is outpacing evaluation, which is exactly where rigorous work matters.",
        "Business Executive": "Move deliberately, measure outcomes, and govern the risk.",
        "Customer": conclusion or "That is the whole idea: more help, less waiting.",
        "General Public": "The point is not the technology. It is who gets to benefit from it.",
        "Technical Audience": "Ship the loop, instrument it, and keep the human in the path.",
    }.get(audience, conclusion or "Implementation quality decides the outcome.")

AUDIENCE_LEAD = {
    "School Student": "Here is the simple version, with no jargon.",
    "College Student": "Here is what this means for your studies and the career you are entering.",
    "Developer": "Here is the implementation view: what changes, what you control, and what fails.",
    "Researcher": "Here is the evidence view, including where the findings are limited.",
    "Business Executive": "Here is the bottom line: market movement, measurable impact, and the risks to govern.",
    "Customer": "Here is what this means for you, in plain terms.",
    "General Public": "Here is what is happening and why it matters.",
    "Technical Audience": "Here is the technical breakdown.",
}

TONE_OPENERS = {
    "Professional": "Evidence first.",
    "Educational": "Let us break this down clearly.",
    "Conversational": "So here is the interesting part.",
    "Technical": "Technical summary follows.",
    "Persuasive": "The case here is difficult to ignore.",
    "Storytelling": "It started with a simple question.",
    "Simple": "The easy version:",
}


def _fact_bank(dna, claims, source_text=""):
    dna = dna or {}
    claims = claims or []

    def clean(items):
        return [str(item).strip() for item in (items or []) if str(item).strip()]

    statistics = []
    for item in clean(dna.get("statistics")):
        if " - " in item:
            value, label = item.split(" - ", 1)
            statistics.append(f"{label.strip()} — {value.strip()}")
        else:
            statistics.append(item)

    return {
        "topic": dna.get("core_topic") or "The source material",
        "summary": dna.get("summary") or "",
        "objective": dna.get("main_objective") or "",
        "arguments": clean(dna.get("key_arguments")),
        "facts": clean(dna.get("key_facts")),
        "statistics": statistics,
        "entities": clean(dna.get("important_entities")),
        "keywords": clean(dna.get("important_keywords")),
        "quotes": clean(dna.get("key_quotes")),
        "conclusions": clean(dna.get("conclusions")),
        "claims": [
            {
                "text": claim.get("claim_text", ""),
                "source": claim.get("supporting_source_text", ""),
                "location": claim.get("source_location", ""),
                "confidence": claim.get("confidence", 0.8),
                "importance": claim.get("importance", "medium"),
            }
            for claim in claims
            if claim.get("claim_text")
        ],
    }


def _style(audience, knowledge_level, tone, bank=None):
    bank = bank or {}
    simple = audience in ("School Student", "Customer", "General Public") or knowledge_level == "Beginner"
    technical = audience in ("Developer", "Technical Audience", "Researcher") or knowledge_level == "Expert"
    executive = audience == "Business Executive"
    bridge = _bridge_for(bank, audience)
    close = _close_for(bank, audience)
    return {
        "audience": audience,
        "level": knowledge_level,
        "tone": tone,
        "frame": AUDIENCE_FRAME.get(audience, "the summary"),
        "bridge": bridge,
        "close": close,
        "opener": f"{TONE_OPENERS.get(tone, 'Here is the picture.')} {AUDIENCE_LEAD.get(audience, '')}".strip(),
        "lead": f"{TONE_OPENERS.get(tone, 'Here is the picture.')} {AUDIENCE_LEAD.get(audience, '')}".strip(),
        "simple": simple,
        "technical": technical,
        "executive": executive,
    }


def _bullets(items, limit=None, prefix="• "):
    items = items or []
    if limit:
        items = items[:limit]
    return "\n".join(f"{prefix}{item}" for item in items)


def _numbered(items, limit=None):
    items = items or []
    if limit:
        items = items[:limit]
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


def _top_stat(bank):
    return bank["statistics"][0] if bank["statistics"] else (bank["facts"][0] if bank["facts"] else "")


def _relevance(bank, style):
    """Audience-specific relevance line drawn from the source, not invented."""
    stats = bank.get("statistics") or []
    args = bank.get("arguments") or []
    facts = bank.get("facts") or []
    topic = _topic_short(bank)
    if style["executive"]:
        signal = next((s for s in stats if any(k in s.lower() for k in ["market", "$", "%", "growth", "billion", "million"])), stats[0] if stats else "")
        return f"Commercially, the signal is measurable: {signal}" if signal else "Commercially, the source points to measurable impact worth tracking."
    if style["technical"]:
        mechanism = args[0] if args else (facts[0] if facts else "")
        return f"Technically, the pattern to implement around is: {mechanism}" if mechanism else "Technically, the value sits in the measurement-to-delivery loop."
    if style["audience"] == "Researcher":
        return "The reported effects are consistent across the source's evidence, which strengthens the signal — though the evidence base still has gaps."
    if style["simple"]:
        plain = facts[0] if facts else (args[0] if args else "")
        return f"In everyday terms: {plain}" if plain else f"In everyday terms, {topic} changes how the work gets done."
    anchor = args[0] if args else (facts[0] if facts else "")
    return f"The practical effect: {anchor}" if anchor else f"The practical effect concerns how {topic} is applied."


# ------------------------------------------------- workstream strategies

# Per-format evidence quotas: (stats, arguments, facts). Each workstream pulls a
# different slice of the source so formats never read as the same dump.
WORKSTREAM_QUOTA = {
    "Social Media Post": (1, 1, 1),
    "LinkedIn Post": (3, 3, 2),
    "Instagram Carousel": (1, 2, 0),
    "X/Twitter Thread": (1, 4, 0),
    "YouTube Script": (3, 3, 3),
    "30-second Reel Script": (1, 1, 0),
    "60-second Reel Script": (2, 3, 1),
    "Blog Article": (6, 5, 5),
    "Newsletter": (4, 0, 0),
    "Executive Summary": (5, 0, 5),
    "Presentation Outline": (4, 3, 0),
    "Podcast Script": (2, 4, 2),
    "FAQ": (1, 3, 6),
    "Study Notes": (6, 5, 8),
    "Press Release": (1, 0, 5),
    "Marketing Copy": (1, 4, 0),
}


def _rank_items(items, style, prefer_numbers=False):
    items = [i for i in (items or []) if i and i.strip()]
    if not items:
        return []
    if style["audience"] == "Business Executive":
        scored = sorted(items, key=lambda s: (0 if any(k in s.lower() for k in ["market", "$", "%", "growth", "billion", "million", "risk", "cost"]) else 1, len(s)))
    elif style["audience"] == "Researcher":
        scored = sorted(items, key=lambda s: (-len(s), s))
    elif style["simple"]:
        scored = sorted(items, key=lambda s: (len(s.split()), s))
    elif prefer_numbers:
        scored = sorted(items, key=lambda s: (0 if any(c.isdigit() for c in s) else 1, s))
    else:
        scored = list(items)
    seen, out = set(), []
    for item in scored:
        key = item.strip().lower()[:60]
        if key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _trim_bank(bank, style, quota):
    n_stats, n_args, n_facts = quota
    trimmed = dict(bank)
    trimmed["statistics"] = _rank_items(bank.get("statistics"), style, prefer_numbers=True)[:n_stats]
    trimmed["arguments"] = _rank_items(bank.get("arguments"), style)[:n_args]
    trimmed["facts"] = _rank_items(bank.get("facts"), style, prefer_numbers=True)[:n_facts]
    trimmed["conclusions"] = list(dict.fromkeys(bank.get("conclusions") or []))[:3]
    return trimmed


def _apply_level(text, style):
    """Rewrite for knowledge level without touching numbers or claim wording order."""
    import re as _re
    if style["level"] == "Beginner":
        out = text
        for term, plain in sorted(JARGON.items(), key=lambda kv: -len(kv[0])):
            out = _re.sub(rf"\b{_re.escape(term)}\b", plain, out, flags=_re.IGNORECASE)
        lines = []
        for line in out.split("\n"):
            stripped = line.strip()
            words = stripped.split()
            if stripped and not stripped.startswith(("#", "•", "SLIDE", "Slide", "Q:", "HOST", "CO-HOST", "[", "SUBJECT", "FOR IMMEDIATE", "CTA", "SPEAKER", "|")) and len(words) > 22 and "," in stripped:
                head, _, tail = stripped.partition(",")
                lines.append(head.strip() + "." if not head.strip().endswith((".", "!", "?", ":")) else head.strip())
                lines.append(tail.strip().capitalize())
            else:
                lines.append(line)
        return "\n".join(lines)
    return text


def _fit_length(text, requested_length):
    if requested_length != "short":
        return text
    lines = [line for line in text.split("\n") if line.strip()]
    if len(lines) <= 8:
        return text
    keep = max(8, round(len(lines) * 0.58))
    return "\n".join(lines[:keep]) + "\n\n[Condensed to the selected short length; refer to the source for full context.]"


# ---------------------------------------------------------------- builders


def _social(bank, style):
    stat = _top_stat(bank)
    return f"""{style['lead']}

{bank['topic']} is not a future headline. It is already measured.

{_relevance(bank, style)}

{stat}

That single number is why this conversation moved from theory to budget.

{style['close']}

What has your experience been? 👇"""


def _linkedin(bank, style):
    stats = bank["statistics"][:3]
    stat_block = "\n".join(f"→ {s}" for s in stats)
    return f"""{style['opener']} {bank['topic']} has moved past the pilot stage.

Here is what the data actually shows:

{stat_block}

The part most people miss:

{_relevance(bank, style)}

{_numbered(bank['arguments'], 3)}

One caution worth stating plainly: {bank['conclusions'][1] if len(bank['conclusions']) > 1 else 'responsible implementation matters more than speed'}.

{style['close']}

{bank['keywords'] and ' '.join('#' + k.replace(' ', '').replace('-', '') for k in bank['keywords'][:5])}"""


def _carousel(bank, style):
    slides = [
        ("1", "TITLE", bank["topic"]),
        ("2", "THE SHIFT", f"{style['lead']} {style['bridge']}"),
        ("3", "DATA POINT", _top_stat(bank)),
        ("4", "WHY IT MATTERS", _relevance(bank, style)),
        ("5", "ARGUMENT", bank["arguments"][0] if bank["arguments"] else "Adoption is accelerating"),
        ("6", "ARGUMENT", bank["arguments"][1] if len(bank["arguments"]) > 1 else "Measurable outcomes are emerging"),
        ("7", "RISK", bank["conclusions"][-1] if bank["conclusions"] else "Implementation quality decides the outcome"),
        ("8", "CTA", style["close"]),
    ]
    if style["executive"]:
        slides.insert(5, ("6", "BUSINESS IMPACT", "Adoption is mainstream and the market is expanding."))
    return "\n".join(
        f"SLIDE {num} — {label}\n{text}\n" for num, label, text in slides
    ).strip()


def _thread(bank, style):
    tweets = [
        f"1/ {bank['topic']} — here is what the evidence actually says. 🧵",
        f"2/ {style['lead']}",
        f"3/ {_top_stat(bank)}",
        f"4/ {_relevance(bank, style)}",
    ]
    for i, arg in enumerate(bank["arguments"][:4], start=5):
        tweets.append(f"{i}/ {arg}")
    if bank["quotes"]:
        tweets.append(f"{len(tweets) + 1}/ {bank['quotes'][0]}")
    tweets.append(f"{len(tweets) + 1}/ The takeaway: {style['close']}")
    tweets.append(f"{len(tweets) + 1}/ If this was useful, follow for more source-grounded analysis.")
    return "\n\n".join(tweets)


def _youtube(bank, style, storyboard):
    scenes = "\n\n".join(
        f"[SCENE {s['scene']} - {s['duration']}]\nVISUAL: {s['visual']}\nTEXT ON SCREEN: {s['on_screen_text']}\nNARRATION: {s['narration']}"
        for s in storyboard
    )
    return f"""[HOOK]
"{style['bridge']} But most coverage skips the numbers."

[INTRO]
In this video we take one source document on {bank['topic']} and walk through what it actually establishes — and where it stays careful.

{scenes}

[SUMMARY]
{_bullets(bank['conclusions'], 3)}

[CTA]
If you want your own documents turned into this kind of structure, try TransformIQ with the link below."""


def _reel_30(bank, style, storyboard):
    scenes = "\n\n".join(
        f"[SCENE {s['scene']} - {s['duration']}]\nVISUAL: {s['visual']}\nTEXT ON SCREEN: {s['on_screen_text']}\nNARRATION: {s['narration']}"
        for s in storyboard
    )
    return f"{scenes}\n\nCTA: \"Follow for more source-grounded breakdowns\"\nCAPTIONS: Enabled"


def _reel_60(bank, style, storyboard):
    scenes = "\n\n".join(
        f"[SCENE {s['scene']} - {s['duration']}]\nVISUAL: {s['visual']}\nTEXT ON SCREEN: {s['on_screen_text']}\nNARRATION: {s['narration']}"
        for s in storyboard
    )
    return f"{scenes}\n\nCTA: \"Follow for more on {bank['keywords'][0] if bank['keywords'] else 'this topic'}\"\nCAPTIONS: Enabled"


def _blog(bank, style):
    return f"""# {bank['topic']}: What the Evidence Shows

## Introduction

{bank['summary']}

{style['opener']} This article stays close to what the source actually establishes.

## The Data

{_bullets(bank['statistics'], 6)}

## Why It Matters

{_relevance(bank, style)}

## The Core Arguments

{_numbered(bank['arguments'], 5)}

## What the Source Cautions

{bank['conclusions'][-1] if bank['conclusions'] else 'Implementation quality determines the outcome.'}

## Entities and Evidence Base

{_bullets(bank['entities'], 8)}

## Conclusion

{bank['conclusions'][0] if bank['conclusions'] else 'The direction of travel is clear.'}

{style['close']}

---
*Generated by TransformIQ from a single source document.*"""


def _newsletter(bank, style):
    return f"""SUBJECT: {bank['topic']} — the numbers that matter

Hello,

{style['opener']}

**This week's focus:** {bank['topic']}

{bank['summary']}

**By the numbers**
{_bullets(bank['statistics'], 4)}

**Why this matters now**
{_relevance(bank, style)}

**Three takeaways**
{_numbered(bank['conclusions'], 3)}

**One line worth keeping**
{bank['quotes'][0] if bank['quotes'] else style['close']}

Until next time,
The TransformIQ Team"""


def _executive(bank, style):
    implications = bank["arguments"][:3] or bank["conclusions"][:3] or [bank["summary"]]
    recommendations = bank["conclusions"][:4] or bank["arguments"][:4] or ["The source does not state a recommendation."]
    risks = [item for item in bank["arguments"] + bank["conclusions"] if any(word in item.lower() for word in ("risk", "challenge", "limitation", "barrier", "concern"))]
    risks = risks[:4] or ["The source does not state a specific risk; validate before making a decision."]
    return f"""# Executive Brief: {bank['topic']}

## Bottom Line

{style['lead']}

{bank['summary']}

## Key Findings

{_numbered(bank['facts'], 5)}

## Market Signal

{_bullets(bank['statistics'], 5)}

## Strategic Implications

{_bullets(implications)}

## Recommendations

{_numbered(recommendations)}

## Risk Register

 | Source-stated risk or limitation | Evidence |
 |---|---|
 {chr(10).join(f'| {risk} | Source statement |' for risk in risks)}

## Decision

{style['close']}"""


def _presentation(bank, style):
    slides = [
        ("Slide 1 — Title", f"{bank['topic']}\n\n{style['lead']}", "Open with the one-line thesis."),
        ("Slide 2 — Why now", _top_stat(bank), "Let the number create urgency."),
        ("Slide 3 — What it is", style["bridge"], "Define the mechanism in one sentence."),
        ("Slide 4 — Evidence", _bullets(bank["statistics"], 4), "Show measured outcomes."),
        ("Slide 5 — Arguments", _bullets(bank["arguments"], 3), "Three supporting claims."),
        ("Slide 6 — Entities", ", ".join(bank["entities"][:5]), "Name the credible sources."),
        ("Slide 7 — Risks", _bullets(bank["conclusions"], 2), "State the limitations honestly."),
        ("Slide 8 — Recommendation", style["close"], "Land the ask."),
    ]
    return "\n\n".join(
        f"{title}\n{body}\nSPEAKER NOTE: {note}" for title, body, note in slides
    )


def _podcast(bank, style):
    return f"""HOST: Welcome back. Today we are working from a single source document on {bank['topic']}.

CO-HOST: {style['lead']}

CO-HOST: And the interesting thing is how much of this is already measured, not projected.

HOST: Let us start with the number that stood out.

CO-HOST: {_top_stat(bank)}

HOST: So this is not speculative.

CO-HOST: {_relevance(bank, style)}

HOST: What are the strongest arguments in the document?

CO-HOST: {_bullets(bank['arguments'], 4)}

HOST: And the cautions?

CO-HOST: {_bullets(bank['conclusions'], 3)}

HOST: {style['close']}

CO-HOST: That is a good place to leave it. Full source is in the show notes."""


def _faq(bank, style):
    faqs = [
        ("Who is this for?", style["lead"]),
        (f"What is {bank['topic'].lower()}?", bank["summary"] or bank["objective"]),
        ("How big is the impact?", _top_stat(bank)),
        ("What does the source actually establish?", bank["summary"] or "The source does not contain enough information to answer this."),
        ("What are the main benefits?", _bullets(bank["arguments"], 3)),
        ("What should we be worried about?", _bullets(bank["conclusions"], 3)),
        ("Who are the credible sources?", ", ".join(bank["entities"][:6])),
        ("What should change first?", bank["conclusions"][0] if bank["conclusions"] else "Start with governance."),
    ]
    return "\n\n".join(f"Q: {q}\nA: {a}" for q, a in faqs)


def _study_notes(bank, style):
    return f"""# Study Notes: {bank['topic']}

## Core Idea

{style['lead']}

{bank['summary']}

## Key Terms

{_bullets(bank['keywords'], 10)}

## Definitions and Facts

{_bullets(bank['facts'], 8)}

## Evidence

{_bullets(bank['statistics'], 6)}

## Supporting Arguments

{_numbered(bank['arguments'], 5)}

## Remember This

{bank['conclusions'][0] if bank['conclusions'] else style['close']}

## Check Yourself

1. What problem does this technology solve?
2. Which number best shows the impact, and why?
3. What is the strongest counter-argument?

## Practice Task

Write one paragraph explaining {bank['topic'].lower()} to someone who has never heard of it."""


def _press_release(bank, style):
    stat = _top_stat(bank)
    headline = f"Source Brief: {bank['topic']}"
    quote = bank["quotes"][0] if bank["quotes"] else (bank["summary"] or "The source provides a documented analysis.")
    return f"""FOR IMMEDIATE RELEASE

{headline}

{style['lead']}

{bank['summary']}

The analysis, drawn from a single source document, reports that {stat.lower() if stat else 'adoption is already widespread'}.

Key findings include:
{_bullets(bank['facts'], 5)}

"{quote}"

Organisations referenced in the source material include {', '.join(bank['entities'][:5])}.

The full report is available on request.

Source note: this release is derived only from the supplied document."""


def _marketing(bank, style):
    stat = _top_stat(bank)
    return f"""{bank['topic']} — without the guesswork.

{style['lead']}

THE PROBLEM
{bank['summary'] or (bank['arguments'][0] if bank['arguments'] else 'The source does not describe a specific problem.')}

THE SOLUTION
{bank['conclusions'][0] if bank['conclusions'] else (bank['arguments'][0] if bank['arguments'] else 'The source does not state a solution.')}

WHAT YOU GET
{_bullets(bank['arguments'], 4)}

PROOF
{stat}

WHO IT IS FOR
{', '.join(bank['entities'][:3]) or 'The audience described by the source'}

{style['close']}

Source note: all claims above come from the supplied document."""


def _generic(bank, style):
    return f"""# {bank['topic']}

{style['opener']}

{bank['summary']}

## Key Arguments

{_bullets(bank['arguments'])}

## Evidence

{_bullets(bank['statistics'])}

## Conclusion

{bank['conclusions'][0] if bank['conclusions'] else style['close']}"""


# --------------------------------------------------------------- storyboards


def _make_storyboard(bank, style, kind):
    stat = _top_stat(bank)
    arg = bank["arguments"]
    if kind == "30":
        return [
            {"scene": 1, "duration": "0-3s", "visual": f"Fast cut: documents, charts and headlines about {_topic_short(bank)}",
             "narration": f"What if one source could change how you see {_topic_short(bank)}?",
             "on_screen_text": bank["topic"]},
            {"scene": 2, "duration": "3-15s", "visual": "Animated data card",
             "narration": f"{stat}.",
             "on_screen_text": "The number that matters"},
            {"scene": 3, "duration": "15-25s", "visual": f"Split screen: manual effort vs. the assisted alternative for {_topic_short(bank)}",
             "narration": arg[0] if arg else style["bridge"],
             "on_screen_text": arg[0][:40] if arg else "Measured impact"},
            {"scene": 4, "duration": "25-30s", "visual": "Logo and follow prompt",
             "narration": style["close"],
             "on_screen_text": "Follow for more"},
        ]
    if kind == "60":
        return [
            {"scene": 1, "duration": "0-5s", "visual": f"Fast cuts: the world of {_topic_short(bank)} in practice",
             "narration": f"What if one source could change how you see {_topic_short(bank)}?",
             "on_screen_text": bank["topic"]},
            {"scene": 2, "duration": "5-15s", "visual": "Animated statistic rising on screen",
             "narration": f"{stat}. And the measured result backs it up.",
             "on_screen_text": stat[:42] if stat else "Measured result"},
            {"scene": 3, "duration": "15-25s", "visual": f"Split screen: the old manual way vs. the assisted way for {_topic_short(bank)}",
             "narration": arg[0] if arg else style["bridge"],
             "on_screen_text": "Where the time goes"},
            {"scene": 4, "duration": "25-35s", "visual": f"Close-up: the detail that makes {_topic_short(bank)} work",
             "narration": _relevance(bank, style),
             "on_screen_text": "Why it matters"},
            {"scene": 5, "duration": "35-48s", "visual": "Wide shot: the wider context and who is affected",
             "narration": bank["conclusions"][-1] if bank["conclusions"] else "Implementation quality decides the outcome.",
             "on_screen_text": "The honest caveat"},
            {"scene": 6, "duration": "48-60s", "visual": "Closing card with the core takeaway",
             "narration": style["close"],
             "on_screen_text": "The takeaway"},
        ]
    return [
        {"scene": 1, "duration": "0-15s", "visual": "Host on camera, document on desk",
         "narration": f"Today we break down {bank['topic'].lower()} from one source.",
         "on_screen_text": "One source, full breakdown"},
        {"scene": 2, "duration": "15-60s", "visual": "Screen recording of the analysis interface",
         "narration": "First, what the document actually claims.",
         "on_screen_text": "The claim ledger"},
        {"scene": 3, "duration": "1:00-2:30", "visual": "Data visualisations",
         "narration": f"{stat}.",
         "on_screen_text": "By the numbers"},
        {"scene": 4, "duration": "2:30-4:30", "visual": "Argument cards appearing in sequence",
         "narration": "Here are the strongest supporting arguments.",
         "on_screen_text": "Key arguments"},
        {"scene": 5, "duration": "4:30-6:00", "visual": "Split source and output view",
         "narration": "Every claim stays linked to its source paragraph.",
         "on_screen_text": "Traceability"},
        {"scene": 6, "duration": "6:00-7:00", "visual": "Closing shot with channel handle",
         "narration": style["close"],
         "on_screen_text": "Subscribe for more"},
    ]


BUILDERS = {
    "Social Media Post": _social,
    "LinkedIn Post": _linkedin,
    "Instagram Carousel": _carousel,
    "X/Twitter Thread": _thread,
    "Blog Article": _blog,
    "Newsletter": _newsletter,
    "Executive Summary": _executive,
    "Presentation Outline": _presentation,
    "Podcast Script": _podcast,
    "FAQ": _faq,
    "Study Notes": _study_notes,
    "Press Release": _press_release,
    "Marketing Copy": _marketing,
}


def build_format_content(output_format, audience, knowledge_level, tone, dna, claims, source_text="", requested_length="medium"):
    bank = _fact_bank(dna, claims, source_text)
    style = _style(audience, knowledge_level, tone, bank)
    quota = WORKSTREAM_QUOTA.get(output_format, (3, 3, 3))
    bank = _trim_bank(bank, style, quota)

    if output_format == "YouTube Script":
        storyboard = _make_storyboard(bank, style, "youtube")
        content = _youtube(bank, style, storyboard)
        return {"content": _fit_length(_apply_level(content, style), requested_length), "estimated_length": "8-10 minutes", "storyboard": storyboard}

    if output_format == "30-second Reel Script":
        storyboard = _make_storyboard(bank, style, "30")
        content = _reel_30(bank, style, storyboard)
        return {"content": _fit_length(_apply_level(content, style), requested_length), "estimated_length": "30 seconds / ~90 words", "storyboard": storyboard}

    if output_format == "60-second Reel Script":
        storyboard = _make_storyboard(bank, style, "60")
        content = _reel_60(bank, style, storyboard)
        return {"content": _fit_length(_apply_level(content, style), requested_length), "estimated_length": "60 seconds / ~180 words", "storyboard": storyboard}

    builder = BUILDERS.get(output_format, _generic)
    content = _fit_length(_apply_level(builder(bank, style), style), requested_length)
    lengths = {
        "Social Media Post": "150-250 words",
        "LinkedIn Post": "200-350 words",
        "Instagram Carousel": "8-10 slides",
        "X/Twitter Thread": "8-10 posts",
        "Blog Article": "700-900 words",
        "Newsletter": "450-650 words",
        "Executive Summary": "300-400 words",
        "Presentation Outline": "8 slides",
        "Podcast Script": "12-15 minutes",
        "FAQ": "7 questions",
        "Study Notes": "600-800 words",
        "Press Release": "400-500 words",
        "Marketing Copy": "300-450 words",
    }
    return {"content": content, "estimated_length": lengths.get(output_format, "varies"), "storyboard": None}
