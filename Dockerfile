# The image tag must match the playwright version pinned in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.64.1-noble
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shc ./shc
RUN useradd -m shc
USER shc
ENV SHC_HOST=0.0.0.0 SHC_PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
# One worker on purpose: reports and rate limits live in memory, and only one browser runs at a time.
CMD ["gunicorn", "-w", "1", "--threads", "4", "--timeout", "900", "-b", "0.0.0.0:8000", "shc.app:app"]
