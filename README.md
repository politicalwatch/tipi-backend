QHLD BACKEND
============

## Requirements

* Python 3.12
* [uv](https://docs.astral.sh/uv/getting-started/installation/)


## Setup

```
git clone git@github.com:politicalwatch/qhld-backend.git
cd qhld-backend
uv sync
set -a
source .env
```

Finally, edit *tipi_backend/settings.py* file with your specific values.


## Load data

*Pending*


## Run

```
uv run python tipi_backend/app.py
```


## Load testing

For exec load testing is necessary install locust. You can initialize the tool:

```
uv run locust
```

This start local server in port 8089.


## Run tests

Tests require a running MongoDB, Redis, and a configured `tipi_backend/settings.py`.

**Inside the container** (recommended — all dependencies available):

```
docker exec -ti qhld-backend sh runtests.sh
```

To restrict to a single test:

```
docker exec -ti qhld-backend pytest -v -s --cov-report html --cov=tipi_backend tests -k test_rate_limit
```

**On the host** (requires local MongoDB, Redis, and settings.py):

```
uv run pytest -v -s --cov-report html --cov=tipi_backend tests
```
