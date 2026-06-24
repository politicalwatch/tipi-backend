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

There are two kinds of tests:

- **unit** (`tests/unit/`) — no infrastructure; run anywhere with no Mongo, Redis,
  broker, or env setup. They test endpoint behavior against a self-contained KB fixture
  (`tests/fixtures/knowledgebase.json`).
- **integration** (`tests/integration/`) — read-only checks against a live prod-copy
  Mongo.

Run everything (the default). Integration tests **auto-skip** when no Mongo is reachable,
so this stays green with zero setup:

```
uv run pytest
```

Run just one kind:

```
uv run pytest -m unit
uv run pytest -m integration
```

Integration tests only actually run when `MONGO_*` points at a reachable prod-copy DB.
From the host against the qhld-infra Mongo (replace the port with whatever `qhld-mongo`
is published on — see `docker ps`):

```
MONGO_HOST=localhost MONGO_PORT=62884 MONGO_USER=qhld MONGO_PASSWORD=… MONGO_DB_NAME=qhlddb \
    uv run pytest -m integration
```

or from inside the qhld-infra `qhld-backend` container (where `MONGO_HOST=mongo`):

```
docker exec -ti qhld-backend pytest -m integration
```

Regenerating the unit-test fixture (only when the `politicas`/`ods` KBs change), from a
mongo with the prod-copy data:

```
docker exec qhld-mongo mongosh -u qhld -p … --quiet --eval \
  'db=db.getSiblingDB("qhlddb"); print(JSON.stringify(db.topics.find(
     {knowledgebase:{$in:["politicas","ods"]}},
     {_id:0,name:1,knowledgebase:1,public:1,"tags.tag":1,"tags.subtopic":1,"tags.regex":1,"tags.shuffle":1}
   ).toArray(), null, 2));' > tests/fixtures/knowledgebase.json
```
