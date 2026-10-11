import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "transformiq.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL DEFAULT 'Demo User',
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        file_type TEXT,
        file_size INTEGER,
        raw_text TEXT,
        page_count INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS content_dna (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        core_topic TEXT,
        summary TEXT,
        main_objective TEXT,
        key_arguments TEXT,
        key_facts TEXT,
        statistics TEXT,
        important_entities TEXT,
        important_keywords TEXT,
        key_quotes TEXT,
        conclusions TEXT,
        target_audiences TEXT,
        tone TEXT,
        complexity_level TEXT,
        estimated_reading_time TEXT,
        content_category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS content_claims (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        claim_text TEXT NOT NULL,
        supporting_source_text TEXT,
        source_location TEXT,
        importance TEXT DEFAULT 'medium',
        confidence REAL DEFAULT 0.8,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS source_chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        chunk_text TEXT NOT NULL,
        page_number INTEGER,
        paragraph_number INTEGER,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS knowledge_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL,
        node_type TEXT,
        label TEXT,
        content TEXT,
        parent_id INTEGER,
        source_text TEXT,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_id INTEGER,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );

    CREATE TABLE IF NOT EXISTS transformations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER,
        source_id INTEGER NOT NULL,
        output_format TEXT NOT NULL,
        target_audience TEXT,
        knowledge_level TEXT,
        tone TEXT,
        status TEXT DEFAULT 'pending',
        transformation_plan TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES sources(id),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );

    CREATE TABLE IF NOT EXISTS generated_outputs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transformation_id INTEGER NOT NULL,
        content TEXT,
        variation_type TEXT DEFAULT 'default',
        storyboard TEXT,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transformation_id) REFERENCES transformations(id)
    );

    CREATE TABLE IF NOT EXISTS quality_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transformation_id INTEGER NOT NULL,
        source_coverage REAL,
        factual_consistency REAL,
        audience_relevance REAL,
        readability REAL,
        unsupported_claims INTEGER DEFAULT 0,
        overall_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transformation_id) REFERENCES transformations(id)
    );

    CREATE TABLE IF NOT EXISTS audit_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transformation_id INTEGER NOT NULL,
        factuality REAL,
        coverage REAL,
        hallucination REAL,
        audience_fit REAL,
        tone_match REAL,
        readability REAL,
        originality REAL,
        overall_score REAL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transformation_id) REFERENCES transformations(id)
    );

    CREATE TABLE IF NOT EXISTS claim_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transformation_id INTEGER NOT NULL,
        claim_id INTEGER,
        generated_statement TEXT,
        verification_status TEXT,
        source_text TEXT,
        confidence REAL,
        FOREIGN KEY (transformation_id) REFERENCES transformations(id)
    );

    CREATE TABLE IF NOT EXISTS document_structure (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL UNIQUE,
        structure TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (source_id) REFERENCES sources(id)
    );
    """)
    for column, ddl in (("section", "TEXT"), ("chunk_type", "TEXT"), ("display_order", "INTEGER")):
        try:
            cursor.execute(f"ALTER TABLE source_chunks ADD COLUMN {column} {ddl}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


init_db()


def save_source(filename, file_type, file_size, raw_text, page_count=1, chunks=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sources (filename, file_type, file_size, raw_text, page_count) VALUES (?, ?, ?, ?, ?)",
        (filename, file_type, file_size, raw_text, page_count),
    )
    source_id = cursor.lastrowid
    if chunks is None:
        paragraphs = [part.strip() for part in raw_text.split("\n\n") if part.strip()]
        chunks = [
            {"text": paragraph, "page": min(page_count, index + 1), "section": None, "type": "text"}
            for index, paragraph in enumerate(paragraphs)
        ]
    for index, chunk in enumerate(chunks):
        cursor.execute(
            """INSERT INTO source_chunks (source_id, chunk_index, chunk_text, page_number,
            paragraph_number, section, chunk_type, display_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source_id,
                chunk.get("chunk_index", index),
                chunk.get("text", ""),
                chunk.get("page", 1),
                index + 1,
                chunk.get("section"),
                chunk.get("type", "text"),
                index,
            ),
        )
    conn.commit()
    conn.close()
    return source_id


def save_document_structure(source_id, structure_json):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM document_structure WHERE source_id = ?", (source_id,))
    cursor.execute(
        "INSERT INTO document_structure (source_id, structure) VALUES (?, ?)",
        (source_id, structure_json),
    )
    conn.commit()
    conn.close()


def get_document_structure(source_id):
    conn = get_db()
    row = conn.execute("SELECT structure FROM document_structure WHERE source_id = ?", (source_id,)).fetchone()
    conn.close()
    if not row or not row["structure"]:
        return None
    try:
        return json.loads(row["structure"])
    except (json.JSONDecodeError, TypeError):
        return None


def get_source(source_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_source_chunks(source_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM source_chunks WHERE source_id = ? ORDER BY chunk_index",
        (source_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_content_dna(source_id, dna_data):
    conn = get_db()
    cursor = conn.cursor()
    existing = cursor.execute("SELECT id FROM content_dna WHERE source_id = ?", (source_id,)).fetchone()
    if existing:
        cursor.execute(
            """UPDATE content_dna SET core_topic=?, summary=?, main_objective=?, key_arguments=?,
            key_facts=?, statistics=?, important_entities=?, important_keywords=?,
            key_quotes=?, conclusions=?, target_audiences=?, tone=?, complexity_level=?,
            estimated_reading_time=?, content_category=? WHERE source_id=?""",
            (
                dna_data.get("core_topic", ""),
                dna_data.get("summary", ""),
                dna_data.get("main_objective", ""),
                json.dumps(dna_data.get("key_arguments", [])),
                json.dumps(dna_data.get("key_facts", [])),
                json.dumps(dna_data.get("statistics", [])),
                json.dumps(dna_data.get("important_entities", [])),
                json.dumps(dna_data.get("important_keywords", [])),
                json.dumps(dna_data.get("key_quotes", [])),
                json.dumps(dna_data.get("conclusions", [])),
                json.dumps(dna_data.get("target_audiences", [])),
                dna_data.get("tone", ""),
                dna_data.get("complexity_level", ""),
                dna_data.get("estimated_reading_time", ""),
                dna_data.get("content_category", ""),
                source_id,
            ),
        )
    else:
        cursor.execute(
            """INSERT INTO content_dna (source_id, core_topic, summary, main_objective, key_arguments,
            key_facts, statistics, important_entities, important_keywords, key_quotes,
            conclusions, target_audiences, tone, complexity_level, estimated_reading_time, content_category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source_id,
                dna_data.get("core_topic", ""),
                dna_data.get("summary", ""),
                dna_data.get("main_objective", ""),
                json.dumps(dna_data.get("key_arguments", [])),
                json.dumps(dna_data.get("key_facts", [])),
                json.dumps(dna_data.get("statistics", [])),
                json.dumps(dna_data.get("important_entities", [])),
                json.dumps(dna_data.get("important_keywords", [])),
                json.dumps(dna_data.get("key_quotes", [])),
                json.dumps(dna_data.get("conclusions", [])),
                json.dumps(dna_data.get("target_audiences", [])),
                dna_data.get("tone", ""),
                dna_data.get("complexity_level", ""),
                dna_data.get("estimated_reading_time", ""),
                dna_data.get("content_category", ""),
            ),
        )
    conn.commit()
    conn.close()


def get_content_dna(source_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM content_dna WHERE source_id = ?", (source_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for field in ["key_arguments", "key_facts", "statistics", "important_entities",
                   "important_keywords", "key_quotes", "conclusions", "target_audiences"]:
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def save_claims(source_id, claims):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM content_claims WHERE source_id = ?", (source_id,))
    for claim in claims:
        cursor.execute(
            """INSERT INTO content_claims (source_id, claim_text, supporting_source_text,
            source_location, importance, confidence) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                source_id,
                claim.get("claim_text", ""),
                claim.get("supporting_source_text", ""),
                claim.get("source_location", ""),
                claim.get("importance", "medium"),
                claim.get("confidence", 0.8),
            ),
        )
    conn.commit()
    conn.close()


def get_claims(source_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM content_claims WHERE source_id = ?", (source_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_knowledge_nodes(source_id, nodes):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM knowledge_nodes WHERE source_id = ?", (source_id,))
    for node in nodes:
        cursor.execute(
            "INSERT INTO knowledge_nodes (source_id, node_type, label, content, parent_id, source_text) VALUES (?, ?, ?, ?, ?, ?)",
            (
                source_id,
                node.get("node_type", ""),
                node.get("label", ""),
                node.get("content", ""),
                node.get("parent_id"),
                node.get("source_text", ""),
            ),
        )
    conn.commit()
    conn.close()


def get_knowledge_nodes(source_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM knowledge_nodes WHERE source_id = ?", (source_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_project(name, source_id=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO projects (name, source_id) VALUES (?, ?)", (name, source_id))
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id


def get_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_transformation(source_id, output_format, target_audience, knowledge_level, tone, project_id=None, plan=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO transformations (source_id, output_format, target_audience, knowledge_level,
        tone, project_id, transformation_plan, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_id, output_format, target_audience, knowledge_level, tone, project_id, plan, "completed"),
    )
    tid = cursor.lastrowid
    conn.commit()
    conn.close()
    return tid


def get_transformations(source_id=None):
    conn = get_db()
    if source_id:
        rows = conn.execute("SELECT * FROM transformations WHERE source_id = ? ORDER BY created_at DESC", (source_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM transformations ORDER BY created_at DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_generated_output(transformation_id, content, variation_type="default", storyboard=None, metadata=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO generated_outputs (transformation_id, content, variation_type, storyboard, metadata) VALUES (?, ?, ?, ?, ?)",
        (transformation_id, content, variation_type, json.dumps(storyboard) if storyboard else None, json.dumps(metadata) if metadata else None),
    )
    output_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return output_id


def get_generated_outputs(transformation_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM generated_outputs WHERE transformation_id = ?", (transformation_id,)).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("storyboard"):
            try:
                d["storyboard"] = json.loads(d["storyboard"])
            except (json.JSONDecodeError, TypeError):
                pass
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


def save_quality_score(transformation_id, scores):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO quality_scores (transformation_id, source_coverage, factual_consistency,
        audience_relevance, readability, unsupported_claims, overall_score) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            transformation_id,
            scores.get("source_coverage", 0),
            scores.get("factual_consistency", 0),
            scores.get("audience_relevance", 0),
            scores.get("readability", 0),
            scores.get("unsupported_claims", 0),
            scores.get("overall_score", 0),
        ),
    )
    conn.commit()
    conn.close()


def get_quality_score(transformation_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM quality_scores WHERE transformation_id = ? ORDER BY created_at DESC LIMIT 1", (transformation_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_verifications(transformation_id, verifications):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM claim_verifications WHERE transformation_id = ?", (transformation_id,))
    for item in verifications:
        cursor.execute(
            """INSERT INTO claim_verifications (transformation_id, claim_id, generated_statement,
            verification_status, source_text, confidence) VALUES (?, ?, ?, ?, ?, ?)""",
            (
                transformation_id,
                item.get("claim_id"),
                item.get("generated_statement") or item.get("claim_text", ""),
                item.get("verification_status", "unsupported"),
                item.get("source_text"),
                item.get("confidence", 0),
            ),
        )
    conn.commit()
    conn.close()


def save_audit_result(transformation_id, audit_data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO audit_results (transformation_id, factuality, coverage, hallucination,
        audience_fit, tone_match, readability, originality, overall_score, details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            transformation_id,
            audit_data.get("factuality", 0),
            audit_data.get("coverage", 0),
            audit_data.get("hallucination", 0),
            audit_data.get("audience_fit", 0),
            audit_data.get("tone_match", 0),
            audit_data.get("readability", 0),
            audit_data.get("originality", 0),
            audit_data.get("overall_score", 0),
            json.dumps(audit_data.get("details", {})),
        ),
    )
    conn.commit()
    conn.close()


def get_analytics():
    conn = get_db()
    total_sources = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
    total_transformations = conn.execute("SELECT COUNT(*) FROM transformations").fetchone()[0]
    total_outputs = conn.execute("SELECT COUNT(*) FROM generated_outputs").fetchone()[0]
    avg_quality = conn.execute("SELECT AVG(overall_score) FROM quality_scores").fetchone()[0] or 0
    verified = conn.execute("SELECT COUNT(*) FROM claim_verifications WHERE verification_status='verified'").fetchone()[0]
    flagged = conn.execute("SELECT COUNT(*) FROM claim_verifications WHERE verification_status='unsupported'").fetchone()[0]

    format_stats = conn.execute(
        "SELECT output_format, COUNT(*) as cnt FROM transformations GROUP BY output_format ORDER BY cnt DESC"
    ).fetchall()

    audience_stats = conn.execute(
        "SELECT target_audience, COUNT(*) as cnt FROM transformations GROUP BY target_audience ORDER BY cnt DESC"
    ).fetchall()

    recent = conn.execute("""
        SELECT t.*, s.filename FROM transformations t
        LEFT JOIN sources s ON t.source_id = s.id
        ORDER BY t.created_at DESC LIMIT 10
    """).fetchall()

    conn.close()
    return {
        "total_sources": total_sources,
        "total_transformations": total_transformations,
        "formats_generated": total_outputs,
        "average_quality": round(avg_quality, 1),
        "verified_claims": verified,
        "flagged_claims": flagged,
        "most_used_formats": [{"format": r["output_format"], "count": r["cnt"]} for r in format_stats],
        "most_used_audiences": [{"audience": r["target_audience"], "count": r["cnt"]} for r in audience_stats],
        "recent_transformations": [dict(r) for r in recent],
        "time_saved_estimate": f"{total_transformations * 25} minutes",
    }
