"""
matcher.py
----------
The core matching engine: turns JD text and resume text into a numeric
"how well does this resume fit this job" score using TF-IDF + Cosine
Similarity (as mandated by the project spec).

ALGORITHM (step by step):
  1. Clean both texts (lowercase, strip noise) -- via text_preprocessing.
  2. Fit a TfidfVectorizer on BOTH documents together (JD + resume), so the
     vocabulary/IDF weights are computed across the same 2-document corpus.
     This is exactly the scikit-learn TF-IDF workflow:
        TF-IDF(word) = TF(word, doc) * IDF(word, corpus)
  3. This yields two TF-IDF vectors: one for the JD, one for the resume.
  4. Compute the Cosine Similarity between those two vectors:
        cosine_similarity = (A . B) / (||A|| * ||B||)
     which produces a float between 0 and 1.
  5. Convert that float to a percentage score (0-100) for the API response,
     e.g. similarity = 0.85 -> match_score = 85.

WHY FIT ON BOTH DOCUMENTS TOGETHER:
  TF-IDF needs a "corpus" to compute IDF (inverse document frequency) --
  i.e. how rare/common each word is. Fitting on just the JD+resume pair
  (rather than some huge external corpus) keeps the comparison focused and
  self-contained, which is the standard lightweight approach for 1-to-1
  document similarity tasks like this.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.text_preprocessing import clean_text


def calculate_match_score(job_description: str, resume_text: str) -> int:
    """
    Compute the JD-vs-resume match score as an integer percentage (0-100).

    Args:
        job_description: Raw job description text.
        resume_text: Raw text extracted from the candidate's resume PDF.

    Returns:
        An integer 0-100 representing how closely the resume matches the JD.
    """
    jd_clean = clean_text(job_description)
    resume_clean = clean_text(resume_text)

    # Guard against empty input -- TfidfVectorizer raises on an all-empty corpus.
    if not jd_clean or not resume_clean:
        return 0

    # Step 1 & 2: Vectorize both documents together.
    # - stop_words="english" removes common filler words (the, and, is, ...)
    #   so the similarity focuses on meaningful technical/role-related terms.
    # - ngram_range=(1, 2) lets the vectorizer capture two-word skill phrases
    #   like "machine learning" as a single feature, not just "machine" and
    #   "learning" separately -- improving match accuracy for multi-word skills.
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))

    try:
        tfidf_matrix = vectorizer.fit_transform([jd_clean, resume_clean])
    except ValueError:
        # Happens if, after stop-word removal, there's no vocabulary left at all.
        return 0

    jd_vector = tfidf_matrix[0:1]
    resume_vector = tfidf_matrix[1:2]

    # Step 3 & 4: Cosine similarity between the two TF-IDF vectors.
    # cosine_similarity returns a 2D array; we need the single scalar value.
    similarity_matrix = cosine_similarity(jd_vector, resume_vector)
    similarity_score = float(similarity_matrix[0][0])  # value between 0.0 and 1.0

    # Step 5: Convert similarity (0.0-1.0) into a percentage score (0-100).
    match_score = round(similarity_score * 100)

    # Clamp defensively in case of floating point edge cases.
    return max(0, min(100, match_score))