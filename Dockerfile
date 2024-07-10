FROM python:3.11-slim-bookworm

RUN pip install psycopg2-binary msgspec sh

COPY logs.py /logs.py

CMD ["python", "/logs.py"]