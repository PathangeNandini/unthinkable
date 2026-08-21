"""
LLM Service
===========
All LLM calls live here. Two responsibilities:

1. extract_resume_data() — turn raw unstructured resume text into structured
   JSON (skills / experience / education).
2. match_resume_to_job() — semantically compare a resume against a job
   description and produce a 1-10 fit score with justification.

Uses Anthropic's Claude API. Requires ANTHROPIC_API_KEY in your environment
(see .env.example). To use OpenAI instead, see the note at the bottom of
this file.
"""
import os
import json
import re
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")


def _extract_json(text: str) -> dict:
    """
    LLMs sometimes wrap JSON in prose or markdown fences despite instructions.
    This pulls out the first {...} block and parses it, raising a clear error
    if nothing usable was found.
    """
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM did not return valid JSON: {e}\nRaw response: {text[:500]}")


def extract_resume_data(resume_text: str) -> dict:
    """
    Prompt the LLM to parse a resume into structured fields.
    Returns: {"skills": [...], "experience": [...], "education": [...]}
    """
    prompt = f"""You are a resume parsing assistant. Extract structured information from the resume below.

Return ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{{
  "skills": ["skill1", "skill2", ...],
  "experience": [
    {{"title": "...", "company": "...", "duration": "...", "description": "..."}}
  ],
  "education": [
    {{"degree": "...", "institution": "...", "year": "..."}}
  ]
}}

Rules:
- "skills" should include technical skills, tools, languages, and frameworks explicitly mentioned or clearly implied by the work described.
- If a field is not present in the resume, use an empty list.
- Do not invent information that isn't in the resume.

Resume text:
\"\"\"
{resume_text}
\"\"\"
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text")
    data = _extract_json(raw)

    data.setdefault("skills", [])
    data.setdefault("experience", [])
    data.setdefault("education", [])
    return data


def match_resume_to_job(resume_text: str, job_description: str) -> dict:
    """
    Prompt the LLM to compare a resume against a job description.
    Returns: {"score": float, "justification": str,
              "matched_skills": [...], "missing_skills": [...]}
    """
    prompt = f"""Compare the following resume with this job description and rate the
candidate's fit on a scale of 1-10, with a clear justification.

Return ONLY valid JSON (no markdown fences, no commentary) in exactly this shape:
{{
  "score": <number between 1 and 10, one decimal place allowed>,
  "justification": "<2-4 sentence explanation of the rating, referencing specific
                     evidence from the resume and requirements from the job description>",
  "matched_skills": ["skill the candidate has that the job wants", ...],
  "missing_skills": ["skill the job wants that the candidate appears to lack", ...]
}}

Scoring guidance:
- 9-10: Excellent match, meets or exceeds nearly all requirements
- 7-8: Strong match, meets most core requirements with minor gaps
- 5-6: Moderate match, meets some requirements but has notable gaps
- 3-4: Weak match, significant gaps in required skills/experience
- 1-2: Poor match, largely unrelated background

Job Description:
\"\"\"
{job_description}
\"\"\"

Resume:
\"\"\"
{resume_text}
\"\"\"
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text")
    data = _extract_json(raw)

    data.setdefault("matched_skills", [])
    data.setdefault("missing_skills", [])
    data["score"] = float(data.get("score", 0))
    return data


# ---------------------------------------------------------------------------
# To use OpenAI instead of Anthropic:
#   pip install openai
#   from openai import OpenAI
#   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
#   response = client.chat.completions.create(
#       model="gpt-4o",
#       messages=[{"role": "user", "content": prompt}],
#       response_format={"type": "json_object"},
#   )
#   raw = response.choices[0].message.content
# The rest of the parsing logic stays the same.
# ---------------------------------------------------------------------------
