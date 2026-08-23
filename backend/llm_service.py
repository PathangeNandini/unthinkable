"""
LLM Service
===========

All LLM calls live here.

Uses OpenRouter API with a free model.
Requires OPENROUTER_API_KEY in your .env file.
"""

import os
import json
import re

from dotenv import load_dotenv
from openai import OpenAI


# Load environment variables from .env
load_dotenv()


# OpenRouter client
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


# Free model router
MODEL = os.getenv("LLM_MODEL", "openrouter/free")


def _extract_json(text: str) -> dict:
    """
    Extract JSON from the LLM response.

    The LLM may sometimes return JSON inside
    markdown code fences or extra text.
    """

    # Try to find JSON inside markdown code fences
    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        text,
        re.DOTALL
    )

    if fenced:
        text = fenced.group(1)

    else:
        # Try to find a JSON object directly
        brace = re.search(
            r"\{.*\}",
            text,
            re.DOTALL
        )

        if brace:
            text = brace.group(0)

    try:
        return json.loads(text)

    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM did not return valid JSON: {e}\n"
            f"Raw response: {text[:500]}"
        )


def _call_llm(prompt: str, max_tokens: int = 2000) -> str:
    """
    Send a prompt to OpenRouter and return the text response.
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=max_tokens
    )

    if not response.choices:
        raise ValueError("OpenRouter returned no choices.")

    raw = response.choices[0].message.content

    print("===== OPENROUTER RESPONSE =====")
    print("CONTENT:", repr(raw))
    print("FINISH:", response.choices[0].finish_reason)
    print("================================")

    if not raw:
        raise ValueError("LLM returned an empty response.")

    return raw

   

def extract_resume_data(resume_text: str) -> dict:
    """
    Extract structured information from a resume.

    Returns:
        {
            "skills": [...],
            "experience": [...],
            "education": [...]
        }
    """

    prompt = f"""
You are a resume parsing assistant.

Extract structured information from the resume below.

Return ONLY valid JSON.
Do not use markdown.
Do not add explanations.

Use exactly this format:

{{
    "skills": [
        "skill1",
        "skill2"
    ],
    "experience": [
        {{
            "title": "...",
            "company": "...",
            "duration": "...",
            "description": "..."
        }}
    ],
    "education": [
        {{
            "degree": "...",
            "institution": "...",
            "year": "..."
        }}
    ]
}}

Rules:

1. Include technical skills, programming languages, tools,
   frameworks and technologies explicitly mentioned in the resume.

2. Do not invent information.

3. If a field is not available, return an empty list.

4. Keep the extracted information concise.

Resume:

{resume_text}
"""

    raw = _call_llm(prompt, max_tokens=2000)

    data = _extract_json(raw)

    data.setdefault("skills", [])
    data.setdefault("experience", [])
    data.setdefault("education", [])

    return data


def match_resume_to_job(
    resume_text: str,
    job_description: str
) -> dict:
    """
    Compare a resume against a job description.

    The LLM evaluates different categories separately.
    Python calculates the final score using fixed weights.
    """

    prompt = f"""
Compare this resume with the job description.

Evaluate the candidate using these four categories:

1. skills_match
2. experience_match
3. projects_match
4. education_match

Give each category a score from 0 to 100.

IMPORTANT:
- Base the scores ONLY on information present in the resume.
- Do not invent skills, experience, projects, or education.
- Compare against the actual requirements in the job description.
- Return ONLY valid JSON.
- Do not use markdown.
- Keep the justification to 1-2 sentences.

Return exactly this structure:

{{
    "skills_match": 90,
    "experience_match": 80,
    "projects_match": 85,
    "education_match": 90,
    "justification": "The candidate has strong technical skills and relevant development experience.",
    "matched_skills": ["Java", "Python", "SQL"],
    "missing_skills": ["Docker"]
}}

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}
"""

    # First attempt
    raw = _call_llm(prompt, max_tokens=2000)

    try:
        data = _extract_json(raw)

    except ValueError:
        # Retry with a simpler prompt
        print("First LLM response was not valid JSON. Retrying...")

        retry_prompt = f"""
Return ONLY a valid JSON object.

Compare the resume with the job description.

Use exactly these fields:

{{
    "skills_match": 0,
    "experience_match": 0,
    "projects_match": 0,
    "education_match": 0,
    "justification": "Short explanation.",
    "matched_skills": [],
    "missing_skills": []
}}

Rules:
- All scores must be between 0 and 100.
- Do not invent information.
- Do not use markdown.
- Do not add any text before or after the JSON.
- Keep the response short.

JOB DESCRIPTION:
{job_description}

RESUME:
{resume_text}
"""

        raw = _call_llm(retry_prompt, max_tokens=1500)

        data = _extract_json(raw)

    # Get category scores
    try:
        skills = float(data.get("skills_match", 0))
        experience = float(data.get("experience_match", 0))
        projects = float(data.get("projects_match", 0))
        education = float(data.get("education_match", 0))

    except (ValueError, TypeError):
        skills = 0.0
        experience = 0.0
        projects = 0.0
        education = 0.0

    # Keep scores between 0 and 100
    skills = max(0, min(100, skills))
    experience = max(0, min(100, experience))
    projects = max(0, min(100, projects))
    education = max(0, min(100, education))

    # Weighted final score
    final_score = (
        skills * 0.50 +
        experience * 0.20 +
        projects * 0.20 +
        education * 0.10
    )

    # Convert 0-100 to 1-10
    final_score = final_score / 10

    data["score"] = round(
        max(1.0, min(10.0, final_score)),
        1
    )

    data.setdefault("justification", "")
    data.setdefault("matched_skills", [])
    data.setdefault("missing_skills", [])

    return data