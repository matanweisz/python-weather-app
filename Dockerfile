FROM python:3.13-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

# Create log directory writable by appuser
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 5000

# Health check using Python stdlib (no curl needed, reduces image size)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=2)" || exit 1

# 2 workers with 4 threads each lets gunicorn handles up to 8 concurrent requests
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "60", "app:app"]
