from locust import HttpLocust, TaskSet, task, between


HOST = 'http://localhost:5000'


class LabelingBehavior(TaskSet):
    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        pass

    def on_stop(self):
        """ on_stop is called when the TaskSet is stopping """
        pass

    def _labeling(self, size=100):
        """ Size can be: 100, 500, 1000, 2000 and 5000 """
        filename = 'tests/tipi-backend/api/scanner_text/w{}.txt'.format(size)
        with open(filename, 'r') as f:
            text = f.read()
        self.client.post('/labels/extract', data={'text': text})

    @task(1)
    def labeling(self):
        self._labeling(100)


class Labeling(HttpLocust):
    host = HOST
    task_set = LabelingBehavior
    wait_time = between(5, 30)


### RESULTS: 100 User, 5 Hatch rate ###

## text => RPS, median (min-max)
## 100  => 6 RPS,   130ms (91-340ms)
## 500  => 2 RPS,   11s (565-22128ms)
## 1000 => 1 RPS,   13s (1359-26649ms)
## 2000 => 0.5 RPS, 18s (1852-34734ms)
## 5000 => 0.1 RPS, 73s (54516-92274ms)
