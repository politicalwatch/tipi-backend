import unittest
import pcre

from tipi_backend.api.business import extract_labels_from_text


class TestBusiness(unittest.TestCase):

    tags = [{
        'topic': 'ODS 1 - Fin de la Pobreza',
        'compiletag': pcre.compile('(?i)Prestaci[oó]n(es)?( por| de) desempleo'),
        'tag': 'Prestaciones por desempleo',
        'subtopic': '1.3'}
    ]

    def test_extract_tags(self):
        text = "¿Considera aceptable el Gobierno recortar las prestaciones por desempleo cuando la economía está creciendo"
        result = extract_labels_from_text(text, self.tags)
        assert 'topics' in result
        assert 'tags' in result
        assert len(result['topics']) == 1
        assert len(result['tags']) == 1

if __name__ == '__main__':
    unittest.main()
