# CARD-0349 Phase 1. python:3.12-slim, not -alpine (the convention every
# other component here uses, e.g. hike-izer-orchestrator/Dockerfile) --
# psycopg2-binary ships manylinux (glibc) wheels only; installing it on
# Alpine's musl libc would fall back to a source build needing gcc/
# postgresql-dev/musl-dev, a real added-complexity cost the slim image
# avoids for one pip package.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/

CMD ["python3", "/app/app.py"]
