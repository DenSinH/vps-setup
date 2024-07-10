FROM python:3.9

RUN pip install psycopg2-binary msgspec sh

COPY logs.py /logs.py

CMD ["python", "/logs.py"]