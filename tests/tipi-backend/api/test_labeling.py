import itertools
import json
import pcre
import pytest
import unittest
import sys
sys.path.append('/app')
from parameterized import parameterized

from tipi_tasks import labeling
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


class TestLabeling(unittest.TestCase):

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
            'ODS 11': ['Zonas de bajas emisiones',
                        'Electrificación de la movilidad',
                        'Transporte público'],
            'ODS 5': ['Ley 1/2004'],
            'ODS 7': ['Ley de transición energética', 'Gases combustibles',
                      'Fracking', 'Fractura hidráulica', 'Transición energética',
                      'Energía renovable, verde, alternativa y limpia',
                      'Energías renovables', 'Biocarburantes', 'IDAE',
                      'Reducción de emisiones'],
            'ODS 8': ['Eficiencia energética', 'Generación de empleo']
        }),
        ('w5000.txt', {
            'ODS 17': ['Remesas'],
            'ODS 5': ['Discriminación por género', 'Igualdad de oportunidades',
                      'Orientación sexual', 'Ley 1/2004', 'Natalidad'],
            'ODS 8': ['Contratación de discapacitados', 'Desempleo', 'INEM',
                      'Formación empresarial', 'Formación y empleo',
                      'Edad de trabajar', 'Conciliacion laboral',
                      'Conciliación mujer', 'Trabajadores de más edad', 'Pensiones'],
        })
    ])
    def test_extract_tags(self, filename, expected_tags):
        with open('tests/tipi-backend/api/scanner_text/' + filename, 'r') as f:
            text = f.read()
        result = extract_labels_from_text(text, TAGS)
        assert 'topics' in result
        assert 'tags' in result

        assert len(result['topics']) == len(expected_tags)
        assert len(result['tags']) == len([v for vs in expected_tags.values() for v in vs])

        for res in result['tags']:
            topic = res.get('topic', '').split('-')[0].strip()
            tag = res.get('tag', '')
            assert tag in expected_tags.get(topic, {})


if __name__ == '__main__':
    unittest.main()
