"""
explanation_generator.py
--------------------------
Turns the raw matched_skills / missing_skills / match_score data into a
short, human-readable explanation sentence -- the "explanation" field in the
API response.

DESIGN NOTES:
- This is fully RULE-BASED (string templates) by default -- no external API
  call, no LLM needed, no API key required. This keeps the project runnable
  out-of-the-box with zero paid dependencies, satisfying the project spec
  exactly as written.
- An OPTIONAL hook (`USE_LLM_EXPLANATION` in config) is included so that, if
  the developer later wants a more natural-language explanation, they can
  flip that flag and provide a GROQ_API_KEY / MISTRAL_API_KEY / GEMINI_API_KEY
  in .env -- the LLM branch is stubbed but not required for the system to work.
  Mistral is used as the open-source LLM option (instead of a closed-source
  OpenAI model) for anyone who wants a free/open-weight-friendly path.
"""

from typing import List

from app.config import settings


def _summarize_matched(matched_skills: List[str]) -> str:
    """Build the 'matched skills' clause of the explanation."""
    if not matched_skills:
        return "Candidate does not match any of the key required skills."

    if len(matched_skills) == 1:
        skills_str = matched_skills[0]
    elif len(matched_skills) == 2:
        skills_str = " and ".join(matched_skills)
    else:
        skills_str = ", ".join(matched_skills[:-1]) + f" and {matched_skills[-1]}"

    return f"Candidate matches key required skills including {skills_str}."


def _summarize_missing(missing_skills: List[str]) -> str:
    """Build the 'missing skills' clause of the explanation."""
    if not missing_skills:
        return "No required skills are missing."

    if len(missing_skills) == 1:
        return f"{missing_skills[0]} is missing."

    skills_str = ", ".join(missing_skills[:-1]) + f" and {missing_skills[-1]}"
    return f"{skills_str} are missing."


def _score_qualifier(match_score: int) -> str:
    """Add a qualitative tone word based on the numeric score band."""
    if match_score >= 80:
        return "an excellent"
    elif match_score >= 60:
        return "a strong"
    elif match_score >= settings.MIN_MATCH_THRESHOLD:
        return "a moderate"
    else:
        return "a weak"


def generate_explanation(
    matched_skills: List[str],
    missing_skills: List[str],
    match_score: int,
    experience: str,
) -> str:
    """
    Compose the final explanation string returned to the API consumer.

    Example output:
      "Candidate matches key required skills including Python, SQL and
       Machine Learning. FastAPI is missing. Overall this is a strong match
       (85%) with 2 Years of experience."
    """
    matched_clause = _summarize_matched(matched_skills)
    missing_clause = _summarize_missing(missing_skills)
    qualifier = _score_qualifier(match_score)

    experience_clause = (
        f" with {experience} of experience" if experience and experience != "Not specified" else ""
    )

    explanation = (
        f"{matched_clause} {missing_clause} "
        f"Overall this is {qualifier} match ({match_score}%){experience_clause}."
    )

    # Optional future upgrade path -- disabled unless explicitly configured.
    if settings.USE_LLM_EXPLANATION and (settings.GROQ_API_KEY or settings.MISTRAL_API_KEY or settings.GEMINI_API_KEY):
        explanation = _try_llm_explanation(matched_skills, missing_skills, match_score, experience, fallback=explanation)

    return explanation


def _try_llm_explanation(
    matched_skills: List[str],
    missing_skills: List[str],
    match_score: int,
    experience: str,
    fallback: str,
) -> str:
    """
    Stub hook for an optional LLM-generated explanation.

    This is intentionally NOT wired to a live API call in this base project
    (no network dependency required to run the system). If you want to
    enable it: implement a Mistral/Groq/Gemini chat call here using the key
    from app.config.settings, prompt it with the matched/missing skills and
    score, and return its response. On any exception, always fall back to
    the rule-based `fallback` string so the API never breaks because of an
    LLM/network issue.

    Mistral (open-source) is used here as the example provider instead of a
    closed-source OpenAI model -- it has an official Python SDK and also
    ships open-weight models you can self-host if you don't want to depend
    on a hosted API at all.
    """
    try:
        # Example (left commented intentionally -- enable by uncommenting and
        # adding the `mistralai` package to requirements.txt if desired):
        #
        # from mistralai import Mistral
        # client = Mistral(api_key=settings.MISTRAL_API_KEY)
        # prompt = (
        #     f"Matched skills: {matched_skills}. Missing skills: {missing_skills}. "
        #     f"Score: {match_score}%. Experience: {experience}. "
        #     f"Write a 1-2 sentence recruiter-style explanation."
        # )
        # response = client.chat.complete(
        #     model="open-mistral-7b",   # open-source Mistral model
        #     messages=[{"role": "user", "content": prompt}],
        # )
        # return response.choices[0].message.content.strip()
        return fallback
    except Exception as e:
        print(f"[explanation_generator] LLM explanation failed, using fallback: {e}")
        return fallback