FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && groupadd --system cofree && useradd --system --gid cofree --home-dir /srv cofree
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

FROM base AS testing
USER root
COPY requirements-dev.txt ./requirements-dev.txt
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
ENV PYTHONPATH=/srv
USER cofree
WORKDIR /tmp
CMD ["pytest", "-q", "/srv/tests"]

FROM base AS runtime
USER cofree
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
