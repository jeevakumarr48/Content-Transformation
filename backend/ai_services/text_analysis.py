"""Heuristic text analysis.

Used when no external LLM provider is configured so that *any* uploaded source
produces content appropriate to that source, instead of a hardcoded sample.
"""

import re

STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had", "her", "was", "one", "our",
    "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old", "see", "two", "way",
    "who", "boy", "did", "use", "that", "with", "this", "from", "they", "have", "will", "would", "there",
    "their", "what", "about", "which", "when", "your", "them", "then", "than", "into", "more", "other", "some",
    "such", "only", "also", "over", "very", "been", "were", "these", "those", "each", "much", "many", "most",
    "because", "between", "through", "during", "before", "after", "above", "below", "while", "where", "being",
    "does", "doing", "done", "having", "should", "could", "might", "must", "shall", "using", "used", "uses",
    "however", "therefore", "thus", "moreover", "furthermore", "although", "though", "whether", "within",
    "without", "across", "along", "among", "around", "based", "including", "includes", "include", "like",
    "just", "even", "well", "make", "made", "makes", "take", "takes", "given", "often", "still", "less",
    "than", "then", "them", "they", "here", "both", "same", "into", "onto", "upon", "per", "via",
}


def _sentences(text):
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _paragraphs(text):
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _clean_heading(line):
    return re.sub(r"^#+\s*", "", line).strip()


def _is_factual(sentence):
    return bool(re.search(r"\d", sentence)) and len(sentence.split()) > 5


def _is_argument(sentence):
    return bool(re.search(r"\b(should|must|need|important|critical|key|essential|risk|challenge|require)\b", sentence, re.I))


def reading_time(text):
    words = len(text.split())
    return f"{max(1, round(words / 200))} minutes"


def analyze_text(raw_text):
    text = (raw_text or "").strip()
    sentences = _sentences(text)
    paragraphs = _paragraphs(text)
    headings = [_clean_heading(line) for line in text.splitlines() if line.strip().startswith("#")]
    title = headings[0] if headings else (paragraphs[0].split(".")[0][:120] if paragraphs else "Untitled Source")

    stats = []
    facts = []
    for sentence in sentences:
        if _is_factual(sentence):
            numbers = re.findall(r"[$€£]?\d[\d,\.]*\s?(?:%|B|M|K|billion|million|percent|bn)?", sentence)
            if any("%" in n or "$" in n or "billion" in n.lower() or "million" in n.lower() for n in numbers):
                stats.append(sentence.strip())
            else:
                facts.append(sentence.strip())
    stats = list(dict.fromkeys(stats))[:8]
    facts = list(dict.fromkeys(facts))[:10]

    if not stats:
        stats = facts[:5]

    arguments = list(dict.fromkeys([s.strip() for s in sentences if _is_argument(s)]))[:6]
    conclusions = [s.strip() for s in sentences[-4:]][:3]

    quotes = re.findall(r"[\"“]([^\"”]{25,240})[\"”]", text)[:4]

    entity_pattern = re.compile(r"\b([A-Z]{2,}(?:\s+[A-Z][a-z]+)?|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")
    raw_entities = entity_pattern.findall(text)
    entity_blocklist = {
        "the report", "this report", "the study", "in addition", "however", "therefore",
        "the market", "the company", "the researchers", "the source", "this analysis",
    }
    entities = []
    for candidate in raw_entities:
        candidate = candidate.strip()
        if candidate.lower() in entity_blocklist or len(candidate) < 3:
            continue
        if candidate not in entities:
            entities.append(candidate)
    entities = entities[:10]

    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{3,}", text.lower())
    freq = {}
    for word in words:
        if word in STOPWORDS:
            continue
        freq[word] = freq.get(word, 0) + 1
    keywords = [w for w, _ in sorted(freq.items(), key=lambda item: item[1], reverse=True)[:12]]

    summary_source = sentences[:3] if sentences else paragraphs[:2]
    summary = " ".join(summary_source)[:600].strip()
    if not summary:
        summary = text[:400]

    audiences = ["General Public", "Technical Audience", "Business Executive"]

    return {
        "core_topic": title,
        "summary": summary,
        "main_objective": f"To communicate the key information about {title}",
        "key_arguments": arguments or facts[:4],
        "key_facts": facts or stats[:5],
        "statistics": stats[:8],
        "important_entities": entities,
        "important_keywords": keywords,
        "key_quotes": quotes,
        "conclusions": conclusions,
        "target_audiences": audiences,
        "tone": "Informative",
        "complexity_level": "Intermediate",
        "estimated_reading_time": reading_time(text),
        "content_category": "Document",
    }


def extract_text_claims(raw_text):
    text = (raw_text or "").strip()
    sentences = _sentences(text)
    paragraphs = _paragraphs(text)
    claims = []
    seen = set()

    for sentence in sentences:
        if not re.search(r"\d", sentence):
            continue
        key = sentence[:60].lower()
        if key in seen:
            continue
        seen.add(key)

        location = "Source"
        for index, paragraph in enumerate(paragraphs):
            if sentence[:40] in paragraph:
                location = f"Section {index + 1}"
                break

        has_percent = bool(re.search(r"%", sentence))
        claims.append({
            "claim_text": sentence.strip(),
            "supporting_source_text": sentence.strip(),
            "source_location": location,
            "importance": "high" if has_percent else "medium",
            "confidence": 0.9 if has_percent else 0.82,
        })
        if len(claims) >= 10:
            break

    if not claims:
        for sentence in sentences[:6]:
            claims.append({
                "claim_text": sentence.strip(),
                "supporting_source_text": sentence.strip(),
                "source_location": "Source",
                "importance": "medium",
                "confidence": 0.75,
            })

    return claims


def build_text_map(raw_text):
    dna = analyze_text(raw_text)
    nodes = [{
        "node_type": "topic",
        "label": dna["core_topic"][:40],
        "content": dna["summary"][:140],
        "parent_id": None,
        "source_text": dna["summary"][:240],
    }]
    for argument in dna["key_arguments"][:4]:
        nodes.append({
            "node_type": "argument",
            "label": " ".join(argument.split()[:6]),
            "content": argument[:140],
            "parent_id": 1,
            "source_text": argument[:240],
        })
    for stat in dna["statistics"][:4]:
        nodes.append({
            "node_type": "evidence",
            "label": " ".join(stat.split()[:6]),
            "content": stat[:140],
            "parent_id": 1,
            "source_text": stat[:240],
        })
    for keyword in dna["important_keywords"][:5]:
        nodes.append({
            "node_type": "concept",
            "label": keyword,
            "content": f"Key concept: {keyword}",
            "parent_id": 1,
            "source_text": dna["summary"][:200],
        })
    for conclusion in dna["conclusions"][:2]:
        nodes.append({
            "node_type": "conclusion",
            "label": " ".join(conclusion.split()[:6]),
            "content": conclusion[:140],
            "parent_id": 1,
            "source_text": conclusion[:240],
        })
    return nodes
