FROM python:3.6-slim

RUN apt-get update && apt-get install -y git gcc libpcre3-dev

COPY . /app
RUN pip install -r /app/requirements.txt
RUN pip install -r /app/requirements-dev.txt

WORKDIR /app

ENV FLASK_APP=tipi_backend/app.py

CMD gunicorn --bind 0.0.0.0:5000 --access-logfile - tipi_backend.wsgi:app --reload
