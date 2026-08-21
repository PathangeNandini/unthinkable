"""Pydantic schemas for API request/response validation."""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobDescriptionCreate(BaseModel):
    title: str
    raw_text: str


class JobDescriptionOut(BaseModel):
    id: int
    title: str
    raw_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: int
    name: str
    filename: Optional[str] = None
    skills: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MatchResultOut(BaseModel):
    id: int
    candidate_id: int
    candidate_name: str
    job_id: int
    job_title: str
    score: float
    justification: str
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class MatchRequest(BaseModel):
    job_id: int
    candidate_ids: Optional[List[int]] = None  # if omitted, match against all candidates
