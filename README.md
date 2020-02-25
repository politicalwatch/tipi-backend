TIPI BACKEND
============

## Requirements

* Python 3.6
* Virtualenv (created and activated)


## Setup

```
git clone git@github.com:politicalwatch/tipi-backend.git
cd tipi-backend
pip install -r requirements_dev.txt
set -a
source .env
python setup.py develop
```

Finally, edit *tipi_backend/settings.py* file with your specific values.


## Load data

*Pending*


## Run

```
python tipi_backend/app.py
```


## Load testing

For exec load testing is necessary install locust. You can initialize the tool:

```
$ locust Labeling
```

This start local server in port 8089.


## Run tests from docker

With docker-compose executing, you should exec the next command:

```
docker exec -ti tipi-backend sh runtests.sh
```

If you only want to execute one test, you can restrict pytest with -k option:

```
docker exec -ti tipi-backend pytest -v -s --cov-report html --cov=tipi_backend tests -k TestLimit
```
