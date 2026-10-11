"""TransformIQ - AI-Powered Content Transformation Intelligence Platform"""
import os
import json
import re
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from base64 import b64encode
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    from backend import database as db
    from backend.ai_services import (
        content_ingestion, content_analyzer, claim_extractor, knowledge_mapper,
        transformation_engine, fact_checker, storyboard_generator, chat_assistant,
    )
    from backend.ai_services import document_pipeline
    from backend.ai_services.demo_data import SAMPLE_DOCUMENT
except ImportError:
    import database as db
    from ai_services import (
        content_ingestion, content_analyzer, claim_extractor, knowledge_mapper,
        transformation_engine, fact_checker, storyboard_generator, chat_assistant,
    )
    from ai_services import document_pipeline
    from ai_services.demo_data import SAMPLE_DOCUMENT


def _public_structure(ir):
    """Trimmed structure safe to persist and send to the client (no duplicate body text)."""
    return {
        "title": ir.get("title"),
        "metadata": ir.get("metadata", {}),
        "stats": ir.get("stats", {}),
        "key_concepts": ir.get("key_concepts", []),
        "entities": ir.get("entities", []),
        "dates": ir.get("dates", []),
        "numbers": ir.get("numbers", []),
        "definitions": ir.get("definitions", []),
        "important_statements": ir.get("important_statements", []),
        "key_facts": ir.get("key_facts", []),
        "tables": ir.get("tables", []),
        "references": ir.get("references", []),
        "sections": [
            {"heading": s["heading"], "level": s["level"], "page": s["page"],
             "paragraphs": len(s["paragraphs"]), "list_items": len(s["list_items"]),
             "tables": len(s["tables"])}
            for s in ir.get("sections", [])
        ],
        "chunks": ir.get("chunks", []),
    }


def _ingest_document(filename, file_bytes):
    """Stages 1-5: return (raw_text, page_count, chunks, public_structure)."""
    ir = document_pipeline.run_pipeline(filename, file_bytes)
    page_count = ir["metadata"].get("page_count", 1)
    structure = _public_structure(ir)
    return ir["full_text"], page_count, ir["chunks"], structure

app = FastAPI(title="TransformIQ API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class SourceIdRequest(BaseModel):
    source_id: int = Field(gt=0)


class TransformRequest(BaseModel):
    source_id: int = Field(gt=0)
    output_format: str = Field(min_length=1, max_length=120)
    output_formats: list[str] = Field(default_factory=list, max_length=16)
    audience: str = Field(default="General Public", min_length=1, max_length=80)
    knowledge_level: str = Field(default="Intermediate", min_length=1, max_length=40)
    tone: str = Field(default="Professional", min_length=1, max_length=40)
    length: str = Field(default="medium", pattern="^(short|medium|detailed)$")


class VariationRequest(BaseModel):
    source_id: int = Field(gt=0)
    output_format: str = Field(min_length=1, max_length=120)
    audience: str = Field(default="General Public", min_length=1, max_length=80)
    knowledge_level: str = Field(default="Intermediate", min_length=1, max_length=40)
    tone: str = Field(default="Professional", min_length=1, max_length=40)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    transformation_id: int | None = Field(default=None, gt=0)
    current_output: str = Field(default="", max_length=100_000)


class ExportRequest(BaseModel):
    content: str = Field(min_length=1, max_length=200_000)
    format: str = Field(default="txt", min_length=1, max_length=20)
    filename: str = Field(default="transformiq_export", min_length=1, max_length=100)
    metadata: dict = Field(default_factory=dict)


async def _read_upload_limited(file: UploadFile) -> bytes:
    parts = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
        parts.append(chunk)
    return b"".join(parts)


@app.get("/api/health")
async def health_check():
    try:
        from backend.ai_services.provider import ai_provider
    except ImportError:
        from ai_services.provider import ai_provider
    return {"status": "ok", "demo_mode": ai_provider.demo_mode, "app": "TransformIQ"}


@app.post("/api/sources/upload")
async def upload_source(file: UploadFile = File(None), text: str = Form(None), url: str = Form(None)):
    try:
        if file:
            fname = file.filename or ""
            ext = os.path.splitext(fname)[1].lower()
            if ext not in [".pdf", ".docx", ".txt", ".md", ".markdown", ".text"]:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

            file_bytes = await _read_upload_limited(file)
            if len(file_bytes) == 0:
                raise HTTPException(status_code=400, detail="File is empty.")

            text_result, pages, chunks, structure = _ingest_document(fname, file_bytes)
            if not text_result.strip():
                raise HTTPException(status_code=400, detail="No readable text was found in this file.")
            source_id = db.save_source(fname, ext.lstrip("."), len(file_bytes), text_result, pages, chunks=chunks)
            db.save_document_structure(source_id, json.dumps(structure))
            return {"source_id": source_id, "filename": fname, "file_type": ext.lstrip("."),
                    "file_size": len(file_bytes), "page_count": pages, "text_preview": text_result[:500],
                    "structure": structure}

        elif url:
            if not url.lower().startswith(("http://", "https://")):
                raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
            text_result, pages = await content_ingestion.extract_from_url(url)
            if not text_result.strip():
                raise HTTPException(status_code=400, detail="The URL returned no readable content.")
            text_result, pages, chunks, structure = _ingest_document("url.txt", text_result.encode("utf-8"))
            if not text_result.strip():
                raise HTTPException(status_code=400, detail="The URL returned no readable content.")
            source_id = db.save_source(url, "url", len(text_result.encode()), text_result, pages, chunks=chunks)
            db.save_document_structure(source_id, json.dumps(structure))
            return {"source_id": source_id, "filename": url, "file_type": "url",
                    "file_size": len(text_result.encode()), "page_count": pages, "text_preview": text_result[:500],
                    "structure": structure}

        elif text:
            if not text.strip():
                raise HTTPException(status_code=400, detail="Pasted text cannot be empty.")
            if len(text.encode("utf-8")) > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Pasted text too large. Maximum 10MB.")
            text_result, pages, chunks, structure = _ingest_document("pasted_text.md", text.encode("utf-8"))
            source_id = db.save_source("Pasted Text", "text", len(text_result.encode()), text_result, pages, chunks=chunks)
            db.save_document_structure(source_id, json.dumps(structure))
            return {"source_id": source_id, "filename": "Pasted Text", "file_type": "text",
                    "file_size": len(text_result.encode()), "page_count": pages, "text_preview": text_result[:500],
                    "structure": structure}

        else:
            raise HTTPException(status_code=400, detail="No file, text, or URL provided.")
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing source: {str(e)}")


@app.get("/api/sources/{source_id}")
async def get_source(source_id: int):
    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@app.get("/api/sources/{source_id}/chunks")
async def get_source_chunks(source_id: int):
    if not db.get_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return db.get_source_chunks(source_id)


@app.get("/api/sources/{source_id}/structure")
async def get_source_structure(source_id: int):
    if not db.get_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    structure = db.get_document_structure(source_id)
    if not structure:
        return {"source_id": source_id, "structure": None,
                "notice": "No structure stored for this source. Re-upload to run the document pipeline."}
    return {"source_id": source_id, "structure": structure}


@app.post("/api/sources/analyze")
async def analyze_source(body: SourceIdRequest):
    source_id = body.source_id

    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    raw_text = source["raw_text"]
    structure = db.get_document_structure(source_id)

    dna = await content_analyzer.analyze_content(raw_text)

    if structure:
        if structure.get("title"):
            dna["core_topic"] = structure["title"].split(":")[0].strip() or structure["title"]
        if structure.get("entities"):
            dna["important_entities"] = structure["entities"]
        if structure.get("key_concepts"):
            dna["important_keywords"] = structure["key_concepts"]
        if structure.get("key_facts"):
            dna["key_facts"] = structure["key_facts"]
        if structure.get("definitions"):
            dna["definitions"] = [f"{d['term']}: {d['definition']}" for d in structure["definitions"]]
        if structure.get("dates"):
            dna["dates"] = structure["dates"]
        if structure.get("numbers") and not dna.get("statistics"):
            dna["statistics"] = structure["numbers"][:8]
        dna["has_tables"] = bool(structure.get("tables"))
        dna["section_count"] = len(structure.get("sections", []))

    db.save_content_dna(source_id, dna)

    claims = await claim_extractor.extract_claims(raw_text)
    if structure and len(claims) < 4:
        existing = {c["claim_text"].strip().lower() for c in claims}
        candidates = list(structure.get("important_statements", [])) + list(structure.get("key_facts", []))
        for statement in candidates:
            if len(claims) >= 8:
                break
            key = statement.strip().lower()
            if not key or key in existing:
                continue
            location = "Source"
            for section in structure.get("sections", []):
                if section.get("heading"):
                    location = section["heading"]
                    break
            claims.append({
                "claim_text": statement.strip(),
                "supporting_source_text": statement.strip(),
                "source_location": location,
                "importance": "high" if any(ch.isdigit() for ch in statement) else "medium",
                "confidence": 0.85,
            })
            existing.add(key)
    if structure:
        for claim in claims:
            source_phrase = (claim.get("supporting_source_text") or claim.get("claim_text") or "")[:80].lower()
            for chunk in structure.get("chunks", []):
                if source_phrase and source_phrase in chunk.get("text", "").lower():
                    claim["source_location"] = f"Page {chunk.get('page', 1)} · {chunk.get('section', 'Source')}"
                    break
    db.save_claims(source_id, claims)

    nodes = await knowledge_mapper.build_knowledge_map(raw_text)
    db.save_knowledge_nodes(source_id, nodes)

    return {
        "source_id": source_id,
        "content_dna": dna,
        "claims_count": len(claims),
        "claims": claims,
        "knowledge_nodes": nodes,
        "knowledge_nodes_count": len(nodes),
        "structure": structure,
    }


@app.post("/api/claims/extract")
async def extract_claims_endpoint(body: SourceIdRequest):
    source_id = body.source_id
    source = db.get_source(source_id) if source_id else None
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    claims = await claim_extractor.extract_claims(source["raw_text"])
    db.save_claims(source_id, claims)
    return {"source_id": source_id, "claims": db.get_claims(source_id)}


@app.post("/api/content-dna")
async def get_content_dna_endpoint(body: SourceIdRequest):
    source_id = body.source_id
    dna = db.get_content_dna(source_id)
    if not dna:
        raise HTTPException(status_code=404, detail="Content DNA not found. Analyze source first.")
    return dna


@app.get("/api/content-dna/{source_id}")
async def get_content_dna_by_id(source_id: int):
    dna = db.get_content_dna(source_id)
    if not dna:
        raise HTTPException(status_code=404, detail="Content DNA not found")
    return dna


@app.get("/api/claims/{source_id}")
async def get_claims(source_id: int):
    return db.get_claims(source_id)


@app.get("/api/knowledge-map/{source_id}")
async def get_knowledge_map(source_id: int):
    nodes = db.get_knowledge_nodes(source_id)
    if not nodes:
        raise HTTPException(status_code=404, detail="Knowledge map not found")
    return nodes


@app.post("/api/knowledge-map")
async def create_knowledge_map(body: SourceIdRequest):
    source_id = body.source_id
    source = db.get_source(source_id) if source_id else None
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    nodes = await knowledge_mapper.build_knowledge_map(source["raw_text"])
    db.save_knowledge_nodes(source_id, nodes)
    return {"source_id": source_id, "nodes": db.get_knowledge_nodes(source_id)}


@app.post("/api/transform")
async def transform_content(body: TransformRequest):
    source_id = body.source_id
    output_formats = body.output_formats or [body.output_format]
    audience = body.audience
    knowledge_level = body.knowledge_level
    tone = body.tone
    requested_length = body.length

    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    raw_text = source["raw_text"]
    dna = db.get_content_dna(source_id) or {}
    claims = db.get_claims(source_id)

    if not dna or not claims:
        raise HTTPException(status_code=409, detail="Analyze the source before generating content.")

    if not output_formats:
        raise HTTPException(status_code=400, detail="Select at least one output format")

    structure = db.get_document_structure(source_id)
    outputs = []
    for output_format in output_formats[:16]:
        plan = await transformation_engine.create_transformation_plan(raw_text, output_format, audience, knowledge_level, tone)
        transformation_id = db.save_transformation(source_id, output_format, audience, knowledge_level, tone, plan=json.dumps(plan))
        result = await transformation_engine.generate_output(raw_text, claims, dna, output_format, audience, knowledge_level, tone, requested_length)
        output_id = db.save_generated_output(transformation_id, result["content"], "default", result.get("storyboard"))
        quality = await fact_checker.calculate_quality_scores(result["content"], raw_text, claims, audience, output_format)
        db.save_quality_score(transformation_id, quality)
        verifications = await fact_checker.verify_claims(result["content"], claims)
        db.save_verifications(transformation_id, verifications)
        audit = await fact_checker.run_quality_audit(result["content"], raw_text, claims, audience, tone, output_format)
        db.save_audit_result(transformation_id, audit)
        validation = await fact_checker.validate_against_source(result["content"], structure, claims)
        outputs.append({
            "transformation_id": transformation_id,
            "output_id": output_id,
            "output_format": output_format,
            "target_audience": audience,
            "knowledge_level": knowledge_level,
            "tone": tone,
            "content": result["content"],
            "storyboard": result.get("storyboard"),
            "quality_scores": quality,
            "audit": audit,
            "verifications": verifications,
            "validation": validation,
            "transformation_plan": plan,
            "estimated_length": result.get("estimated_length", ""),
        })

    return {"outputs": outputs, **outputs[0]}


@app.post("/api/transform/variations")
async def generate_variations(body: VariationRequest):
    source_id = body.source_id
    output_format = body.output_format
    audience = body.audience
    knowledge_level = body.knowledge_level
    tone = body.tone

    source = db.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    dna = db.get_content_dna(source_id) or {}
    claims = db.get_claims(source_id)

    variations = await transformation_engine.generate_variations(
        source["raw_text"], claims, dna, output_format, audience, knowledge_level, tone
    )
    for index, variation in enumerate(variations):
        variation["output_id"] = -(index + 1)
        variation["output_format"] = output_format
        variation["target_audience"] = audience
        variation["quality_scores"] = await fact_checker.calculate_quality_scores(
            variation.get("content", ""), source["raw_text"], claims, audience, output_format
        )
        variation["verifications"] = await fact_checker.verify_claims(variation.get("content", ""), claims)
    return {"variations": variations}


@app.get("/api/transform/{transformation_id}")
async def get_transformation(transformation_id: int):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM transformations WHERE id = ?", (transformation_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Transformation not found")
    result = dict(row)
    result["outputs"] = db.get_generated_outputs(transformation_id)
    result["quality_scores"] = db.get_quality_score(transformation_id)
    return result


@app.get("/api/transformations")
async def get_transformations(source_id: int | None = None):
    return db.get_transformations(source_id)


@app.post("/api/transform/{transformation_id}/verify")
async def verify_transformation(transformation_id: int):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM transformations WHERE id = ?", (transformation_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Transformation not found")
    transformation = dict(row)
    source = db.get_source(transformation["source_id"])
    claims = db.get_claims(transformation["source_id"])
    outputs = db.get_generated_outputs(transformation_id)

    verifications = []
    for output in outputs:
        v = await fact_checker.verify_claims(output["content"], claims)
        verifications.extend(v)

    db.save_verifications(transformation_id, verifications)

    return {"transformation_id": transformation_id, "verifications": verifications}


@app.post("/api/transform/{transformation_id}/audit")
async def audit_transformation(transformation_id: int):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM transformations WHERE id = ?", (transformation_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Transformation not found")
    transformation = dict(row)
    source = db.get_source(transformation["source_id"])
    claims = db.get_claims(transformation["source_id"])
    outputs = db.get_generated_outputs(transformation_id)

    if not outputs:
        raise HTTPException(status_code=400, detail="No outputs to audit")

    audit = await fact_checker.run_quality_audit(
        outputs[0]["content"], source["raw_text"], claims,
        transformation["target_audience"], transformation["tone"], transformation["output_format"]
    )
    db.save_audit_result(transformation_id, audit)
    return audit


@app.post("/api/transform/{transformation_id}/regenerate")
async def regenerate_transformation(transformation_id: int, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    conn = db.get_db()
    row = conn.execute("SELECT * FROM transformations WHERE id = ?", (transformation_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Transformation not found")

    transformation = dict(row)
    source = db.get_source(transformation["source_id"])
    dna = db.get_content_dna(transformation["source_id"]) or {}
    claims = db.get_claims(transformation["source_id"])

    result = await transformation_engine.generate_output(
        source["raw_text"], claims, dna, transformation["output_format"],
        transformation["target_audience"], transformation["knowledge_level"], transformation["tone"]
    )

    output_id = db.save_generated_output(transformation_id, result["content"], "default", result.get("storyboard"))
    quality = await fact_checker.calculate_quality_scores(
        result["content"], source["raw_text"], claims,
        transformation["target_audience"], transformation["output_format"]
    )
    db.save_quality_score(transformation_id, quality)
    verifications = await fact_checker.verify_claims(result["content"], claims)
    db.save_verifications(transformation_id, verifications)
    audit = await fact_checker.run_quality_audit(
        result["content"], source["raw_text"], claims,
        transformation["target_audience"], transformation["tone"], transformation["output_format"]
    )
    db.save_audit_result(transformation_id, audit)
    validation = await fact_checker.validate_against_source(
        result["content"], db.get_document_structure(transformation["source_id"]), claims
    )
    plan = await transformation_engine.create_transformation_plan(
        source["raw_text"], transformation["output_format"], transformation["target_audience"],
        transformation["knowledge_level"], transformation["tone"]
    )

    return {
        "transformation_id": transformation_id,
        "output_id": output_id,
        "output_format": transformation["output_format"],
        "target_audience": transformation["target_audience"],
        "knowledge_level": transformation["knowledge_level"],
        "tone": transformation["tone"],
        "content": result["content"],
        "quality_scores": quality,
        "audit": audit,
        "verifications": verifications,
        "validation": validation,
        "transformation_plan": plan,
        "storyboard": result.get("storyboard"),
    }


@app.post("/api/chat")
async def chat(body: ChatRequest):
    message = body.message.strip()
    transformation_id = body.transformation_id
    current_output = body.current_output

    context = {}
    if transformation_id:
        conn = db.get_db()
        row = conn.execute("SELECT * FROM transformations WHERE id = ?", (transformation_id,)).fetchone()
        conn.close()
        if row:
            transformation = dict(row)
            source_id = transformation["source_id"]
            outputs = db.get_generated_outputs(transformation_id)
            if outputs and not current_output.strip():
                current_output = outputs[-1]["content"]
            context = {
                "dna": db.get_content_dna(source_id) or {},
                "claims": db.get_claims(source_id),
                "output_format": transformation["output_format"],
                "audience": transformation["target_audience"],
                "knowledge_level": transformation["knowledge_level"],
                "tone": transformation["tone"],
            }
            source = db.get_source(source_id)
            context["source_text"] = source["raw_text"] if source else ""

    response = await chat_assistant.chat_assistant(message, current_output, context.get("source_text", ""), context)
    return response


@app.get("/api/projects")
async def get_projects():
    return db.get_projects()


@app.post("/api/projects")
async def create_project(request: Request):
    body = await request.json()
    project_id = db.save_project(body.get("name", "New Project"), body.get("source_id"))
    return {"project_id": project_id, "name": body.get("name", "New Project")}


@app.post("/api/export")
async def export_content(body: ExportRequest):
    content = body.content
    format_type = body.format.lower().strip()
    filename = re.sub(r"[^a-zA-Z0-9_-]+", "_", body.filename).strip("_")[:80] or "transformiq_export"

    if format_type == "markdown":
        return {"content": content, "filename": f"{filename}.md", "mime_type": "text/markdown"}
    elif format_type == "json":
        return {"content": json.dumps({"content": content, "metadata": body.metadata}, indent=2),
                "filename": f"{filename}.json", "mime_type": "application/json"}
    elif format_type == "docx":
        from docx import Document
        from io import BytesIO
        document = Document()
        for paragraph in content.splitlines():
            document.add_paragraph(paragraph)
        buffer = BytesIO()
        document.save(buffer)
        return {"content_base64": b64encode(buffer.getvalue()).decode("ascii"),
                "filename": f"{filename}.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "binary": True}
    elif format_type == "pdf":
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from io import BytesIO
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            y = 750
            for line in content.splitlines():
                if y < 50:
                    pdf.showPage()
                    y = 750
                pdf.drawString(54, y, line[:110])
                y -= 15
            pdf.save()
            return {"content_base64": b64encode(buffer.getvalue()).decode("ascii"),
                    "filename": f"{filename}.pdf", "mime_type": "application/pdf", "binary": True}
        except ImportError:
            return {"content": content, "filename": f"{filename}.txt", "mime_type": "text/plain", "notice": "Install reportlab for PDF export"}
    else:
        return {"content": content, "filename": f"{filename}.txt", "mime_type": "text/plain"}


@app.get("/api/analytics")
async def get_analytics():
    return db.get_analytics()


@app.post("/api/demo/load")
async def load_demo():
    filename = "AI in Modern Education - Research Report.md"
    text_result, pages, chunks, structure = _ingest_document(filename, SAMPLE_DOCUMENT.encode("utf-8"))
    source_id = db.save_source(filename, "md", len(SAMPLE_DOCUMENT.encode()), text_result, pages, chunks=chunks)
    db.save_document_structure(source_id, json.dumps(structure))
    return {"source_id": source_id, "filename": filename,
            "message": "Demo document loaded successfully", "structure": structure}
