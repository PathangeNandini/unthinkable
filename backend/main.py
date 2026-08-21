"""
Smart Resume Screener — FastAPI backend.

Endpoints:
  POST /job-descriptions          create a job description
  GET  /job-descriptions          list job descriptions
  POST /candidates/upload         upload + parse a resume (PDF/TXT)
  GET  /candidates                list all candidates
  GET  /candidates/{id}           get one candidate with structured data
  POST /match                     run LLM matching for a job against candidates
  GET  /match/{job_id}            get ranked match results for a job (shortlist view)

Run with: uvicorn main:app --reload
"""
import json
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import Base, engine, get_db
import models
import schemas
from resume_parser import extract_text_from_upload
from llm_service import extract_resume_data, match_resume_to_job

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Resume Screener", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "Smart Resume Screener API"}


# ---------------------------------------------------------------------------
# Job Descriptions
# ---------------------------------------------------------------------------

@app.post("/job-descriptions", response_model=schemas.JobDescriptionOut)
def create_job_description(payload: schemas.JobDescriptionCreate, db: Session = Depends(get_db)):
    job = models.JobDescription(title=payload.title, raw_text=payload.raw_text)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get("/job-descriptions", response_model=list[schemas.JobDescriptionOut])
def list_job_descriptions(db: Session = Depends(get_db)):
    return db.query(models.JobDescription).order_by(desc(models.JobDescription.created_at)).all()


# ---------------------------------------------------------------------------
# Candidates (resume upload + LLM structured extraction)
# ---------------------------------------------------------------------------

@app.post("/candidates/upload", response_model=schemas.CandidateOut)
async def upload_candidate(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    try:
        raw_text = extract_text_from_upload(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        structured = extract_resume_data(raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")

    candidate = models.Candidate(
        name=name,
        filename=file.filename,
        raw_text=raw_text,
        skills=json.dumps(structured["skills"]),
        experience=json.dumps(structured["experience"]),
        education=json.dumps(structured["education"]),
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@app.get("/candidates", response_model=list[schemas.CandidateOut])
def list_candidates(db: Session = Depends(get_db)):
    return db.query(models.Candidate).order_by(desc(models.Candidate.created_at)).all()


@app.get("/candidates/{candidate_id}", response_model=schemas.CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    candidate = db.query(models.Candidate).filter(models.Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

@app.post("/match", response_model=list[schemas.MatchResultOut])
def run_matching(payload: schemas.MatchRequest, db: Session = Depends(get_db)):
    job = db.query(models.JobDescription).filter(models.JobDescription.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    query = db.query(models.Candidate)
    if payload.candidate_ids:
        query = query.filter(models.Candidate.id.in_(payload.candidate_ids))
    candidates = query.all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found to match")

    results = []
    for candidate in candidates:
        try:
            result = match_resume_to_job(candidate.raw_text, job.raw_text)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM matching failed for candidate {candidate.id}: {e}")

        match = models.MatchResult(
            candidate_id=candidate.id,
            job_id=job.id,
            score=result["score"],
            justification=result["justification"],
            matched_skills=json.dumps(result["matched_skills"]),
            missing_skills=json.dumps(result["missing_skills"]),
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        results.append(schemas.MatchResultOut(
            id=match.id,
            candidate_id=candidate.id,
            candidate_name=candidate.name,
            job_id=job.id,
            job_title=job.title,
            score=match.score,
            justification=match.justification,
            matched_skills=result["matched_skills"],
            missing_skills=result["missing_skills"],
            created_at=match.created_at,
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


@app.get("/match/{job_id}", response_model=list[schemas.MatchResultOut])
def get_shortlist(job_id: int, db: Session = Depends(get_db)):
    """Returns the most recent match result per candidate for a given job, ranked by score."""
    job = db.query(models.JobDescription).filter(models.JobDescription.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found")

    matches = (
        db.query(models.MatchResult)
        .filter(models.MatchResult.job_id == job_id)
        .order_by(desc(models.MatchResult.score))
        .all()
    )

    seen_candidates = set()
    output = []
    for m in matches:
        if m.candidate_id in seen_candidates:
            continue
        seen_candidates.add(m.candidate_id)
        output.append(schemas.MatchResultOut(
            id=m.id,
            candidate_id=m.candidate_id,
            candidate_name=m.candidate.name,
            job_id=job.id,
            job_title=job.title,
            score=m.score,
            justification=m.justification,
            matched_skills=json.loads(m.matched_skills or "[]"),
            missing_skills=json.loads(m.missing_skills or "[]"),
            created_at=m.created_at,
        ))
    return output
