"""
main.py
-------
Application entrypoint for the Smart Resume Screening System.

RESPONSIBILITIES:
  1. IMPORTS -- pull in FastAPI itself, the CORS middleware, our config
     (settings), and the resume_routes router that holds the actual
     /screen-resume endpoint logic.
  2. FASTAPI INITIALIZATION -- create the `app` object with metadata
     (title/description/version) that powers the auto-generated docs at
     /docs and /redoc.
  3. MIDDLEWARE -- attach CORS so the API can be called from a browser-based
     frontend on a different origin during development/demos.
  4. ROUTER REGISTRATION -- mount resume_routes.router onto the app so its
     endpoints (POST /screen-resume, GET /health) become reachable.
  5. UVICORN EXECUTION -- when this file is run directly (`python -m
     app.main` or `python app/main.py`), start the Uvicorn ASGI server using
     host/port/debug values pulled from settings (which itself reads .env).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import resume_routes

# --- 2. FastAPI initialization ---------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered resume screening system that compares resumes against a "
        "job description using TF-IDF + Cosine Similarity, extracts skills "
        "and experience, and returns a match score with explanation."
    ),
    version=settings.APP_VERSION,
)

# --- 3. Middleware -----------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. Router registration ---------------------------------------------------
# All endpoints defined in resume_routes.py become live under the root path.
# (No extra prefix is added here since the spec asks for exactly POST
# /screen-resume -- not /api/v1/screen-resume etc.)
app.include_router(resume_routes.router, tags=["Resume Screening"])


@app.get("/", tags=["Root"])
async def root():
    """Basic landing route confirming the API is up, with a pointer to the docs."""
    return {
        "message": f"{settings.APP_NAME} is running.",
        "docs": "/docs",
        "health_check": "/health",
    }


# --- 5. Uvicorn execution -----------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )