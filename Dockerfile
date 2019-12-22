FROM tipi-backend:base

COPY . /app
RUN pip install -r /app/requirements.txt

WORKDIR /app

ENV FLASK_APP=tipi_backend/app.py

CMD gunicorn --bind 0.0.0.0:5000 --access-logfile - tipi_backend.wsgi:app --reload
