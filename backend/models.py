"""
ORM models: Candidate (parsed resume), JobDescription, and MatchResult
(the LLM-computed fit score + justification linking a candidate to a job).
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255))
    raw_text = Column(Text)  # full extracted resume text

    # Structured fields extracted by the LLM, stored as JSON strings
    skills = Column(Text)        # JSON list, e.g. ["Python", "SQL", "AWS"]
    experience = Column(Text)    # JSON list of {title, company, years, description}
    education = Column(Text)     # JSON list of {degree, institution, year}

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    matches = relationship("MatchResult", back_populates="candidate", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    matches = relationship("MatchResult", back_populates="job", cascade="all, delete-orphan")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"))
    job_id = Column(Integer, ForeignKey("job_descriptions.id"))

    score = Column(Float, nullable=False)          # 1-10 LLM-computed fit score
    justification = Column(Text, nullable=False)   # LLM's written reasoning
    matched_skills = Column(Text)                  # JSON list of overlapping skills
    missing_skills = Column(Text)                  # JSON list of gaps

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="matches")
    job = relationship("JobDescription", back_populates="matches")
