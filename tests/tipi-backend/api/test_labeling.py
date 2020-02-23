import itertools
import json
import pcre
import pytest
import unittest
import sys
sys.path.append('/app')
from parameterized import parameterized

from tipi_alerts import labeling
from tipi_backend.api.endpoints import cache
from tipi_backend.app import create_app
from tipi_backend.settings import Config


# Extract tags from topics
with open('tests/tipi-backend/api/topics.json', 'r') as f:
    topics = json.loads(f.read())

TAGS = []
delimiter = '.*'
for topic in topics:
    for tag in topic['tags']:
        if tag['shuffle']:
            for permutation in itertools.permutations(tag['regex'].split(delimiter)):
                TAGS.append({
                    'topic': topic['name'],
                    'subtopic': tag['subtopic'],
                    'tag': tag['tag'],
                    'compiletag': pcre.compile('(?i)' + delimiter.join(permutation))
                })
        else:
            TAGS.append({
                'topic': topic['name'],
                'subtopic': tag['subtopic'],
                'tag': tag['tag'],
                'compiletag': pcre.compile('(?i)' + tag['regex'])
            })

# initialize app
Config.TESTING = True
Config.USE_ALERTS = True
Config.LABELING_MAX_WORD = 5001
app = create_app(config=Config)
cache.set(Config.CACHE_TAGS, TAGS, timeout=5*60)


class TestLabeling(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    @parameterized.expand([
        ('w100.txt', {'ODS 16': ['Elusión y evasión fiscal']}),
        ('w500.txt', {
            'ODS 5': ['Ley 1/2004', 'Aborto', 'Feto'],
            'ODS 6': ['Contaminación del agua'],
        }),
        ('w1000.txt', {
            'ODS 16': ['Rendición de cuentas'],
            'ODS 5': ['Empoderamiento de las mujeres y las niñas', 'Ley 1/2004'],
            'ODS 7': ['Estrategia Española de Desarrollo Sostenible'],
        }),
        ('w2000.txt', {
            'ODS 11': ['Electrificación de la movilidad', 'Transporte público'],
            'ODS 5': ['Ley 1/2004'],
            'ODS 7': ['Ley de transición energética', 'Gases combustibles',
                      'Fracking', 'Fractura hidráulica', 'Transición energética',
                      'Energía renovable, verde, alternativa y limpia',
                      'Energías renovables', 'Biocarburantes', 'IDAE',
                      'Eficiencia energética'],
            'ODS 8': ['Eficiencia energética', 'Generación de empleo']
        }),
        ('w5000.txt', {
            'ODS 17': ['Remesas'],
            'ODS 5': ['Orientación sexual', 'Ley 1/2004', 'Natalidad'],
            'ODS 8': ['Desempleo', 'INEM', 'Edad de trabajar',
                      'Conciliacion laboral', 'Trabajadores de más edad',
                      'Pensiones'],
        })
    ])
    def test_extract_tags(self, filename, expected_tags):
        with open('tests/tipi-backend/api/scanner_text/' + filename, 'r') as f:
            text = f.read()
        res = self.client.post('/labels/extract', data={'text': text})
        self.assertEqual(res.status_code, 200)
        res_json = res.json
        self.assertTrue('topics' in res_json)
        self.assertTrue('tags' in res_json)

        print(res_json)
        self.assertEqual(len(res_json['topics']), len(expected_tags))
        self.assertEqual(len(res_json['tags']), len([v for vs in expected_tags.values() for v in vs]))

        for res in res_json['tags']:
            topic = res.get('topic', '').split('-')[0].strip()
            tag = res.get('tag', '')
            print(topic, tag)
            self.assertTrue(tag in expected_tags.get(topic, {}))

    def test_labeling_num_words(self):
        Config.LABELING_MAX_WORD = 10
        text = "test " * 11
        res = self.client.post('/labels/extract', data={'text': text})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json.startswith(Config.TASK_LABELING_TEXT.split()[0]))


if __name__ == '__main__':
    unittest.main()
