FROM python:3.6-slim

RUN apt-get update && apt-get install -y git gcc libpcre3-dev tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat

COPY requirements.txt requirements-dev.txt /app/
RUN pip install -r /app/requirements.txt

COPY . /app/
WORKDIR /app

ENV FLASK_APP=tipi_backend/app.py

CMD gunicorn --bind 0.0.0.0:5000 --access-logfile - tipi_backend.wsgi:app
