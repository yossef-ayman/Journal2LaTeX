FROM python:3.11-slim

# Install system runtime dependencies for conversion & compilation pipeline:
# - pandoc: DOCX -> LaTeX conversion and media extraction
# - texlive-*: TeX Live distribution and LaTeX engine (pdflatex, packages, fonts)
# - latexmk: Automated multi-pass LaTeX compilation builder
# - poppler-utils: PDF utility tools (pdftoppm, pdfinfo)
# - libreoffice: Headless document rendering fallback
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-pictures \
    texlive-science \
    latexmk \
    poppler-utils \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy python dependencies file and install
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY backend/ /app/backend/

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend
ENV PORT=8000

# Start FastAPI application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
