# Smart Resume Screener

Parses resumes, extracts structured skill/experience/education data, and uses
an LLM to semantically score how well each candidate fits a job description
— with a written justification for every score.

## Architecture

```
smart-resume-screener/
├── backend/
│   ├── main.py            # FastAPI app & all API routes
│   ├── models.py          # SQLAlchemy ORM models (Candidate, JobDescription, MatchResult)
│   ├── schemas.py         # Pydantic request/response schemas
│   ├── database.py        # DB engine/session setup (SQLite by default)
│   ├── resume_parser.py   # PDF/TXT → raw text extraction
│   └── llm_service.py     # All LLM calls: structured extraction + matching
├── frontend/
│   └── index.html         # Single-file dashboard (vanilla JS, no build step)
├── sample_data/           # A sample resume + job description for testing
├── requirements.txt
├── .env.example
└── README.md
```

**Flow:**
1. Recruiter posts a job description (`POST /job-descriptions`).
2. Recruiter uploads a resume (`POST /candidates/upload`) — the backend
   extracts raw text (`resume_parser.py`), then calls the LLM
   (`llm_service.extract_resume_data`) to pull out structured skills,
   experience, and education, which are stored in SQLite.
3. Recruiter clicks "Run matching" (`POST /match`) — for each candidate,
   the backend sends the resume text + job description to the LLM
   (`llm_service.match_resume_to_job`), which returns a 1–10 fit score,
   a written justification, and matched/missing skills.
4. Results are stored and displayed ranked by score, highest first
   (`GET /match/{job_id}` for the persisted shortlist).

The LLM is used for **semantic understanding**, not just keyword matching —
it can tell that "built REST APIs with FastAPI" satisfies a requirement for
"API development experience" even without exact keyword overlap.

## Setup

### 1. Get an LLM API key
This project uses **Anthropic's Claude API**.
- Go to [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
- Sign up / log in, create a new API key
- New accounts typically get some free trial credit, enough to test this project

(Want to use OpenAI instead? See the comment block at the bottom of
`backend/llm_service.py` — it's a small swap.)

### 2. Install dependencies
```bash
cd smart-resume-screener
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure your environment
```bash
cp .env.example .env
# Edit .env and paste your ANTHROPIC_API_KEY
```

### 4. Run the backend
```bash
cd backend
uvicorn main:app --reload
```
API is now live at `http://localhost:8000`. Interactive API docs (auto-generated
by FastAPI) are at `http://localhost:8000/docs`.

### 5. Open the dashboard
Just open `frontend/index.html` in your browser (double-click it, or serve it
with `python3 -m http.server` from the `frontend/` folder). It talks to the
API at `http://localhost:8000`.

### 6. Try it with the sample data
- Paste `sample_data/sample_job_description.txt` into the job description form
- Upload `sample_data/sample_resume.txt` as a resume
- Click "Run matching" to see the LLM score it

## LLM Prompts Used

**Resume extraction** (`extract_resume_data` in `llm_service.py`) — asks the
model to return strict JSON with `skills`, `experience`, and `education`
arrays, instructed not to invent information not present in the resume.

**Match scoring** (`match_resume_to_job` in `llm_service.py`) — the core
prompt, modeled directly on the brief's example:

> "Compare the following resume with this job description and rate fit on
> 1–10 with justification."

Extended with explicit scoring bands (9–10 excellent, 7–8 strong, 5–6
moderate, 3–4 weak, 1–2 poor) so scores are consistent across candidates,
and asked to return `matched_skills` / `missing_skills` alongside the score
so the dashboard can show *why* a score landed where it did — not just the
number.

Both prompts request JSON-only responses; `_extract_json()` in
`llm_service.py` defensively strips markdown fences or stray prose in case
the model doesn't comply perfectly.

## API Reference

| Method | Path                     | Description                                  |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/job-descriptions`      | Create a job description                     |
| GET    | `/job-descriptions`      | List job descriptions                        |
| POST   | `/candidates/upload`     | Upload + LLM-parse a resume (multipart form)  |
| GET    | `/candidates`            | List all candidates                          |
| GET    | `/candidates/{id}`       | Get one candidate's structured data           |
| POST   | `/match`                 | Run LLM matching for a job vs. candidates     |
| GET    | `/match/{job_id}`        | Get the ranked shortlist for a job            |

Full interactive docs at `/docs` once the server is running.

## Database

Uses SQLite by default (`resume_screener.db`, created automatically on first
run) — zero setup needed for a demo. To use PostgreSQL instead, set
`DATABASE_URL` in `.env` to a standard SQLAlchemy connection string, e.g.
`postgresql://user:password@localhost/resume_screener`.

## Notes on scope / what to extend for production

- **Auth**: none included — add an auth layer (API keys, OAuth, etc.) before
  deploying anywhere public.
- **Scanned/image PDFs**: `resume_parser.py` extracts text directly and will
  raise a clear error on image-only PDFs; add OCR (e.g. `pytesseract`) if you
  need to support those.
- **Rate limits / cost**: each resume upload and each match makes one LLM
  call. For large batches, consider batching or a queue.
- **CORS**: currently wide open (`allow_origins=["*"]`) for easy local
  testing — restrict this before deploying.
