# TransformIQ - AI-Powered Content Transformation Intelligence Platform

## Project Structure

```
Content Transformation/
├── backend/
│   ├── main.py                  # FastAPI application
│   ├── database.py              # SQLite database layer
│   ├── .env                     # Environment variables
│   ├── requirements.txt         # Python dependencies
│   ├── uploads/                 # Uploaded files
│   ├── transformiq.db           # SQLite database (auto-created)
│   ├── ai_services/
│   │   ├── provider.py          # AI provider abstraction
│   │   ├── demo_data.py         # Demo mode data
│   │   ├── content_ingestion.py # File processing (PDF, DOCX, TXT, URL)
│   │   ├── document_pipeline.py  # Structured extraction, cleaning, IR, chunks
│   │   ├── content_analyzer.py  # Content DNA analyzer
│   │   ├── claim_extractor.py   # Factual claim extractor
│   │   ├── knowledge_mapper.py  # Knowledge map builder
│   │   ├── transformation_engine.py # Content transformation
│   │   ├── fact_checker.py      # Verification, validation & quality scoring
│   │   ├── content_builders.py  # Source-grounded format builders
│   │   ├── storyboard_generator.py # Video storyboard generation
│   │   └── chat_assistant.py    # Contextual AI assistant
│   └── routes/
│       └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # Entry point
│   │   ├── App.tsx              # Application shell and workflows
│   │   ├── App.css               # Application styling
│   │   ├── pipeline.css          # Structure/validation styling
│   │   ├── index.css             # Global styles
│   │   └── api.ts                # API client
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── package.json
└── README.md
```

## Installation

### Backend

```bash
cd backend
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

```
AI_API_KEY=your_api_key_here
AI_PROVIDER=openai
AI_MODEL=gpt-3.5-turbo
DEMO_MODE=true
FRONTEND_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
APP_PORT=8003
```

**Demo Mode**: The application works without an API key. Set `DEMO_MODE=true` or leave `AI_API_KEY` empty.

## Running

### Windows one-click launcher

Double-click `start-transformiq.bat`. It opens the backend, frontend, and browser automatically.

Double-click `stop-transformiq.bat` to stop both development servers.

### Backend (Port 8003)

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8003 --reload
```

### Frontend (Port 5174)

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

Open: http://localhost:5174

## Demo Instructions

1. Click **"Try Live Demo"** in the sidebar
2. Source is automatically loaded
3. Go to **Content DNA** to see analysis
4. Go to **Transformation Studio**
5. Select format (e.g., 60-second Reel Script)
6. Select audience (e.g., College Student)
7. Click **Transform Content**
8. View generated output, quality scores, storyboard, and verification
9. Use the **Transform Assistant** to edit the current output

### Transform Assistant

The assistant edits the current output rather than starting over. It understands:

- `Make this simpler` — plain language, shorter sentences
- `Create a stronger hook` — new opening drawn from the source
- `Remove technical jargon` — replaces technical terms with plain equivalents
- `Make this suitable for LinkedIn` — reformats with hashtags
- `Create a 30-second version` — condenses and keeps a CTA
- `Turn this into a presentation` — converts to slide outline
- `Add the key statistics` — appends the source statistics
- `Explain this claim` — returns the claim, evidence and confidence
- `Where did this statement come from?` — traces to a source location

It also switches audience or tone on request (for example "make this for executives"),
rebuilding the output in that voice while keeping the facts unchanged.

### Content behaviour without an API key

Every uploaded document is analyzed from its own text (topic, summary, facts,
statistics, entities, keywords, claims and knowledge map). Each of the 16 output
formats has its own structure and is adapted to the selected audience, knowledge
level and tone. No output falls back to a generic template.

## API Documentation

Backend runs at http://localhost:8003 with Swagger docs at http://localhost:8003/docs

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/demo/load | Load sample document |
| POST | /api/sources/upload | Upload file/text/URL |
| POST | /api/sources/analyze | Analyze source content |
| GET | /api/content-dna/{id} | Get Content DNA |
| GET | /api/claims/{id} | Get extracted claims |
| GET | /api/knowledge-map/{id} | Get knowledge map |
| POST | /api/transform | Generate one or many transformations with `output_formats` |
| GET | /api/transformations | List transformation history |
| POST | /api/transform/variations | Generate 3 variations |
| POST | /api/claims/extract | Extract and persist source claims |
| POST | /api/knowledge-map | Build and persist the source map |
| GET | /api/sources/{id}/chunks | Read source evidence chunks |
| GET | /api/sources/{id}/structure | Read structured document representation |
| GET | /api/analytics | Get analytics data |
| POST | /api/chat | AI assistant chat |
| POST | /api/export | Export content |

## Implemented Features

1. Content DNA extraction
2. Knowledge Map visualization
3. Claim traceability with source verification
4. 16 output formats
5. 8 target audiences
6. 3 knowledge levels
7. 7 tone options
8. Transformation quality scoring
9. AI content auditing
10. Video storyboard generation
11. Content variation engine (3 versions)
12. Side-by-side source verification
13. Contextual AI chat assistant
14. Export (TXT, Markdown, JSON, DOCX, PDF)
15. Analytics dashboard with charts
16. Transformation history
17. Demo mode with sample document
18. PDF, DOCX, TXT, URL file processing
19. Structured document IR with sections, tables, definitions, dates and numbers
20. Semantic chunks with source metadata
21. Source validation with missing-number and unsupported-claim checks
22. Automated regression suite in `regression_check.py`

## Known Limitations

- Demo mode uses deterministic source-grounded generation when no API key is configured
- OCR requires a local Tesseract installation for scanned PDFs
- No user authentication (single-user prototype)
- URL extraction may fail for JavaScript-heavy sites
- YouTube URL processing not implemented in demo mode

## Tests

```bash
python regression_check.py --base-url http://127.0.0.1:8003
cd frontend
npm run lint
npm run build
```
