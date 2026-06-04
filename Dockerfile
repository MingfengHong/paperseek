# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860

WORKDIR /app

RUN useradd --create-home --shell /bin/sh paperseek

COPY pyproject.toml README.md LICENSE ./
COPY paperseek ./paperseek
COPY paperseek_core ./paperseek_core

RUN python -m pip install --upgrade pip \
    && python -m pip install .

USER paperseek

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; port=os.environ.get('PORT', '7860'); urllib.request.urlopen('http://127.0.0.1:' + port + '/api/sources', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn paperseek.web_app:app --host 0.0.0.0 --port ${PORT:-7860}"]
