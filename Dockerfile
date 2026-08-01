# Base image matches this repo's actual local Python version (verified via
# `python3 --version` -> 3.9.6), not guessed.
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only what backend/app.py actually reads/serves at startup (verified by
# reading it): the app module itself, frontend/index.html (served at "/"),
# and output/*.json + output/*.jsonl (gaps, rejected candidates, routing,
# notification drafts). scripts/, data/, tests/, logs/ are pipeline-authoring
# concerns, not runtime dependencies of the API -- not copied.
COPY backend/ backend/
COPY frontend/ frontend/
COPY output/ output/

EXPOSE 8420

CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8420"]
