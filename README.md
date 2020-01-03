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
python setup.py develop
cp tipi_backend/settings.py.example tipi_backend/settings.py
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
