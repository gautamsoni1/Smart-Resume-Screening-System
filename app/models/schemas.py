"""
schemas.py
----------
Pydantic models that define the "shape" of data flowing in and out of the API.

WHY:
- FastAPI uses these to auto-validate incoming JSON / form data and to
  auto-generate the OpenAPI (Swagger) docs at /docs.
- Keeping them separate from route logic means routes.py stays clean and the
  contract of the API is documented in exactly one place.

NOTE ON FILE UPLOAD:
Because /screen-resume accepts a PDF file (multipart/form-data) together with
a JSON-like field (job_description), the *request* side is mostly handled by
FastAPI's `UploadFile` + `Form(...)` directly in the route signature -- not by
a Pydantic model (Pydantic models don't natively parse multipart file parts).
We still define `JobDescriptionRequest` for any JSON-only endpoints / future
use (e.g. a pure-text "compare two strings" endpoint), and it documents the
expected shape clearly.
"""

from typing import List
from pydantic import BaseModel, Field


class JobDescriptionRequest(BaseModel):
    """
    Request body shape for endpoints that accept ONLY a job description
    (no file). Used for validation / docs and reusable in future endpoints.
    """
    job_description: str = Field(
        ...,
        min_length=10,
        description="Full text of the job description to match resumes against.",
        examples=["Python Developer with FastAPI, SQL and Machine Learning"],
    )


class ScreeningResult(BaseModel):
    """
    Response shape returned by POST /screen-resume for a single resume.
    This matches exactly the format requested in the project spec.
    """
    resume_name: str = Field(..., description="Original filename of the uploaded resume PDF.")
    match_score: int = Field(..., ge=0, le=100, description="Resume-to-JD match score as a percentage (0-100).")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both the resume and the JD.")
    missing_skills: List[str] = Field(default_factory=list, description="Skills required by the JD but not found in the resume.")
    experience: str = Field(..., description="Total years of experience extracted from the resume, e.g. '2 Years'.")
    explanation: str = Field(..., description="Human-readable summary of why the candidate got this score.")

    class Config:
        json_schema_extra = {
            "example": {
                "resume_name": "resume.pdf",
                "match_score": 85,
                "matched_skills": ["Python", "SQL", "Machine Learning"],
                "missing_skills": ["FastAPI"],
                "experience": "2 Years",
                "explanation": (
                    "Candidate matches most required skills including Python, SQL and "
                    "Machine Learning. FastAPI is missing."
                ),
            }
        }


class BatchScreeningResponse(BaseModel):
    """
    Wraps multiple ScreeningResult objects for the case where several resumes
    are uploaded in a single request, ranked best-match first.
    """
    job_description: str
    total_resumes_screened: int
    results: List[ScreeningResult]


class ErrorResponse(BaseModel):
    """Standard error shape returned on failures (bad file type, parse error, etc.)."""
    detail: str