## 🚀 Live Demo

Try the deployed application:

👉 https://smart-resumescreener.netlify.app/

For an easy test, use the sample job description provided in:

`sample_data/Sample_Job_Description.pdf`

You can upload any suitable resume and run the matching process to see the candidate score, justification, matched skills, and missing skills.

# Smart Resume Screener

Smart Resume Screener is a full-stack application that helps recruiters evaluate multiple candidates against job descriptions.

The application:

- Parses resumes in PDF/TXT format
- Extracts structured candidate information using an LLM
- Stores candidates and job descriptions in SQLite
- Supports multiple resumes for the same job
- Compares candidates against job requirements
- Evaluates skills, experience, projects, and education separately
- Calculates a final candidate score using fixed weights
- Shows matched and missing skills
- Ranks candidates from highest to lowest score
- Allows recruiters to delete uploaded candidates
- Provides a FastAPI backend and a simple web dashboard

---

## Features

### Resume Management

- Upload resumes in PDF or TXT format
- Automatically extract resume text
- Extract:
  - Skills
  - Experience
  - Education
- Store candidate information in the database
- View multiple uploaded candidates
- Delete candidates when they are no longer required

### Job Description Management

- Create and save job descriptions
- Store multiple job descriptions
- Select a job description from the dashboard
- Match multiple candidates against the selected job

### AI-Based Resume Matching

Each candidate is evaluated using four categories:

1. Skills Match
2. Experience Match
3. Projects Match
4. Education Match

Each category receives a score from **0–100**.

The final score is calculated by Python using fixed weights:

| Category | Weight |
|----------|--------|
| Skills | 50% |
| Experience | 20% |
| Projects | 20% |
| Education | 10% |

The final weighted score is converted to a **1–10 rating**.

The system also returns:

- Matched skills
- Missing skills
- Short justification

This makes the screening process more transparent than simply returning a single AI-generated score.

---

## Architecture

```text
smart-resume-screener/
│
├── backend/
│   ├── main.py
│   │   └── FastAPI application and API routes
│   │
│   ├── models.py
│   │   └── SQLAlchemy database models
│   │
│   ├── schemas.py
│   │   └── Pydantic request/response schemas
│   │
│   ├── database.py
│   │   └── Database connection and session management
│   │
│   ├── resume_parser.py
│   │   └── PDF/TXT text extraction
│   │
│   └── llm_service.py
│       └── LLM-based resume extraction and matching
│
├── frontend/
│   └── index.html
│       └── Web dashboard
│
├── sample_data/
│   ├── sample resume
│   └── sample job description
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md