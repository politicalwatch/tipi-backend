FROM python:3.12-slim

RUN apt-get update && apt-get install -y git gcc poppler-utils tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat antiword

COPY requirements.txt requirements-dev.txt /app/
RUN pip install -r /app/requirements.txt

COPY . /app/
WORKDIR /app

ENV FLASK_APP=tipi_backend/app.py

CMD gunicorn --bind 0.0.0.0:5000 --access-logfile - tipi_backend.wsgi:app --timeout 120
