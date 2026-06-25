"""
resume_routes.py
------------------
Defines the FastAPI router that exposes the resume-screening functionality
over HTTP.

ENDPOINT: POST /screen-resume
- Accepts multipart/form-data with:
    - job_description: str  (Form field)
    - resumes: List[UploadFile]  (one or more PDF files)
- Pipeline per resume:
    1. Validate file extension (.pdf only) and size.
    2. Save the upload to disk (uploads/ folder) -- see _save_upload().
    3. Extract raw text via pdf_parser.extract_text_from_pdf().
    4. Extract skills from JD text AND resume text via skill_extractor.
    5. Diff matched vs missing skills (set operations on JD skills vs resume skills).
    6. Extract experience via experience_extractor.
    7. Compute match_score via matcher.calculate_match_score() (TF-IDF + cosine).
    8. Build the explanation via explanation_generator.
    9. Assemble a ScreeningResult and append to the response list.
- If multiple resumes are uploaded, results are sorted by match_score
  descending so the best-fit candidate appears first.
- Each resume is processed independently inside a try/except so that ONE bad
  file (corrupt PDF, scanned image with no text, etc.) doesn't fail the
  entire batch -- it's reported as a per-file error instead.
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import ScreeningResult, BatchScreeningResponse
from app.services.pdf_parser import extract_text_from_pdf, PDFParsingError
from app.services.skill_extractor import extract_skills
from app.services.experience_extractor import extract_experience_label
from app.services.matcher import calculate_match_score
from app.services.explanation_generator import generate_explanation

router = APIRouter()


def _validate_file(file: UploadFile) -> None:
    """Reject non-PDF files early with a clear 400 error instead of failing deep in parsing."""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}' for '{filename}'. Only PDF files are accepted.",
        )


def _save_upload(file: UploadFile) -> str:
    """
    Persist the uploaded file to the configured uploads/ directory using a
    UUID-prefixed filename to avoid collisions between candidates who happen
    to upload files with the same name (e.g. two "resume.pdf" uploads).

    Returns the full path on disk where the file was saved.
    """
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    destination = os.path.join(settings.UPLOAD_DIR, safe_name)

    with open(destination, "wb") as out_file:
        content = file.file.read()

        # Enforce max file size (read length check after reading is simplest
        # given UploadFile's stream-based API at small resume-file scale).
        max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"'{file.filename}' exceeds the {settings.MAX_FILE_SIZE_MB}MB upload limit.",
            )

        out_file.write(content)

    return destination


def _process_single_resume(file: UploadFile, job_description: str, jd_skills: List[str]) -> ScreeningResult:
    """
    Run the full screening pipeline for exactly one uploaded resume file.
    Raises HTTPException-friendly errors that the caller can catch and
    convert into a per-file error entry instead of crashing the whole batch.
    """
    saved_path = _save_upload(file)

    try:
        resume_text = extract_text_from_pdf(saved_path)
    except PDFParsingError as e:
        raise ValueError(str(e))
    finally:
        # Clean up the saved file after processing -- we only needed it on
        # disk long enough for pdfplumber to read it. Comment this out if you
        # want to retain uploaded resumes for audit/history purposes.
        if os.path.exists(saved_path):
            os.remove(saved_path)

    resume_skills = extract_skills(resume_text)

    matched_skills = sorted(set(jd_skills) & set(resume_skills))
    missing_skills = sorted(set(jd_skills) - set(resume_skills))

    match_score = calculate_match_score(job_description, resume_text)
    experience = extract_experience_label(resume_text)

    explanation = generate_explanation(
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        match_score=match_score,
        experience=experience,
    )

    return ScreeningResult(
        resume_name=file.filename,
        match_score=match_score,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        experience=experience,
        explanation=explanation,
    )


@router.post(
    "/screen-resume",
    response_model=BatchScreeningResponse,
    summary="Screen one or more resumes against a job description",
)
async def screen_resume(
    job_description: str = Form(
        ...,
        description="Full text of the job description to match resumes against.",
    ),
    resumes: List[UploadFile] = File(
        ...,
        description="One or more resume PDF files to screen.",
    ),
):
    """
    Main screening endpoint.

    Form fields (multipart/form-data):
      - job_description: str
      - resumes: one or more PDF files

    Returns a BatchScreeningResponse containing a ScreeningResult per resume,
    sorted by match_score descending (best match first).
    """
    if not job_description or len(job_description.strip()) < 10:
        raise HTTPException(status_code=400, detail="job_description must be at least 10 characters long.")

    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume PDF must be uploaded.")

    # Pre-validate all files before doing any expensive work.
    for file in resumes:
        _validate_file(file)

    jd_skills = extract_skills(job_description)

    results: List[ScreeningResult] = []
    errors: List[dict] = []

    for file in resumes:
        try:
            result = _process_single_resume(file, job_description, jd_skills)
            results.append(result)
        except ValueError as e:
            errors.append({"resume_name": file.filename, "error": str(e)})
        except Exception as e:
            errors.append({"resume_name": file.filename, "error": f"Unexpected error: {e}"})

    # Best matches first.
    results.sort(key=lambda r: r.match_score, reverse=True)

    response_payload = BatchScreeningResponse(
        job_description=job_description,
        total_resumes_screened=len(results),
        results=results,
    )

    if errors:
        # Still return the successful results, but surface which files failed
        # via an additional key on the JSON body (not part of the strict
        # response_model, so we build the raw dict ourselves here).
        body = response_payload.model_dump()
        body["errors"] = errors
        return JSONResponse(content=body)

    return response_payload


@router.get("/health", summary="Health check")
async def health_check():
    """Simple liveness probe used by uptime monitors / load balancers."""
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}