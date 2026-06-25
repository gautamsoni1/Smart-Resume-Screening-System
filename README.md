# Smart Resume Screening System (AI-Powered)

An AI-powered resume screening backend built with **FastAPI**. It compares
candidate resumes (PDF) against a Job Description (JD) and returns a
**match score**, **matched/missing skills**, **extracted experience**, and a
**human-readable explanation** — computed using **TF-IDF + Cosine
Similarity** and regex-based extraction (no database, no external API key
required).

---

## 1. Setup Steps

### Prerequisites
- Python 3.11+ installed
- pip (comes with Python)

### Step-by-step

```bash
# 1. Go to the project folder
cd smart_resume_screening

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Set up environment variables
copy .env.example .env         # Windows
cp .env.example .env           # Mac/Linux
```

> `.env` already comes with safe defaults (port 8000, upload limits, etc.).
> **No API keys are required** to run the core system — TF-IDF/cosine
> similarity and regex matching run fully locally. The optional
> `GROQ_API_KEY` / `MISTRAL_API_KEY` / `GEMINI_API_KEY` fields are only for
> a future LLM-based explanation upgrade — leave them blank.

### Troubleshooting setup
| Issue | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run commands from inside `smart_resume_screening/`, not inside `app/` |
| Import errors after editing a file | Delete stale `__pycache__` folders: `Get-ChildItem -Recurse -Filter "__pycache__" \| Remove-Item -Recurse -Force` (PowerShell) |
| `pip install` fails | Confirm Python version: `python --version` (needs 3.11+) |

---

## 2. How to Run the API

### Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
or
```bash
python -m app.main
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Test it (Swagger UI — easiest way)
Open in browser:
```
http://localhost:8000/docs
```
1. Find **POST /screen-resume** → click **"Try it out"**
2. Fill `job_description` (text) and upload one or more resume PDFs under `resumes`
3. Click **Execute** → see the JSON response below

### Test it (curl)
```bash
curl -X POST "http://localhost:8000/screen-resume" \
  -F "job_description=Python Developer with FastAPI, SQL and Machine Learning" \
  -F "resumes=@/path/to/resume.pdf"
```

### Test it (Python)
```python
import requests

url = "http://localhost:8000/screen-resume"
data = {"job_description": "Python Developer with FastAPI, SQL and Machine Learning"}
files = {"resumes": open("resume.pdf", "rb")}

response = requests.post(url, data=data, files=files)
print(response.json())
```

### Sample response
```json
{
  "job_description": "Python Developer with FastAPI, SQL and Machine Learning",
  "total_resumes_screened": 1,
  "results": [
    {
      "resume_name": "resume.pdf",
      "match_score": 85,
      "matched_skills": ["Python", "SQL", "Machine Learning"],
      "missing_skills": ["FastAPI"],
      "experience": "2 Years",
      "explanation": "Candidate matches key required skills including Python, SQL and Machine Learning. FastAPI is missing. Overall this is a strong match (85%) with 2 Years of experience."
    }
  ]
}
```

Other endpoints:
- `GET /health` — liveness check
- `GET /` — root info + links to docs

---

## 3. Approach Explanation

### Pipeline (what happens on every request)
```
1. Job description text  +  uploaded resume PDF(s)
2. PDF → raw text              (pdfplumber, pdf_parser.py)
3. Text cleaning                (lowercase, strip noise, text_preprocessing.py)
4. Skill extraction              regex + alias normalization → skill_extractor.py
        - applied to BOTH job description and resume text
        - matched_skills  = JD skills ∩ resume skills
        - missing_skills  = JD skills − resume skills
5. Experience extraction        regex patterns ("2 years experience", "3+ years",
                                  "Worked for 4 years", etc.) → experience_extractor.py
6. Match scoring                  TF-IDF vectorization + Cosine Similarity → matcher.py
7. Explanation generation       rule-based template using steps 4-6 → explanation_generator.py
8. JSON response                 returned via FastAPI, sorted by match_score (best first)
```

### Why TF-IDF + Cosine Similarity (matching algorithm)
1. Both the JD and the resume text are vectorized together using
   **scikit-learn's `TfidfVectorizer`** — this assigns weight to each word
   based on how important/rare it is across the two documents.
2. **Cosine similarity** is computed between the JD vector and the resume
   vector — a value between `0.0` (no overlap) and `1.0` (identical).
3. That similarity is converted to a percentage:
   ```
   similarity = 0.85  →  match_score = 85
   ```
4. `ngram_range=(1,2)` is used so two-word skill phrases like "machine
   learning" are captured as a single meaningful term, not split into two
   unrelated words.

### Why regex for skills/experience (not an LLM)
- **Deterministic & fast** — no network call, no API key, no per-request cost.
- **Predictable output** — a fixed skill database (`SKILL_DATABASE` +
  `SKILL_ALIASES` in `skill_extractor.py`) means results are consistent and
  easy to extend (just add a skill name to the list).
- An **optional LLM hook** exists in `explanation_generator.py` (Mistral
  open-source model) for a more natural-language explanation later, but
  it's disabled by default — the system works fully offline without it.

### Why no database
- The system is **stateless by design**: each request is processed
  independently, the uploaded PDF is read and then deleted immediately
  after extraction (`resume_routes.py`), and nothing is persisted.
- This matches a pure "screen-on-demand" API use case. If you need
  screening **history** (saving past results, ranking candidates over
  time), that would require adding MongoDB/PostgreSQL — not included in
  this version, but easy to bolt on (`repositories/` + `services/` layer)
  if needed later.

### Error handling approach
- Invalid file type (non-PDF) → rejected early with a clear `400` error.
- Corrupted/unreadable/scanned-image PDFs → caught per-file; that resume is
  reported in an `errors` array instead of crashing the whole batch.
- Multiple resumes in one request are processed independently — one bad
  file never blocks the others.