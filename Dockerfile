# ESD Memory demo app (Streamlit on port 8501)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ESD_DATA_DIR=/app/data \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken

WORKDIR /app

COPY requirements.txt .
# Also download the tokenizer file now, so the container never fetches it at runtime.
RUN pip install -r requirements.txt \
 && python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"

COPY . .

RUN useradd --create-home --uid 10001 app \
 && mkdir -p /app/data \
 && chown -R app:app /app/data \
 && chmod +x /app/deploy/entrypoint.sh

USER app
EXPOSE 8501
ENTRYPOINT ["/app/deploy/entrypoint.sh"]
