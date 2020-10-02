import codecs
import logging
import pickle
from textract import process
from os.path import splitext
import tempfile

from flask import request, abort
from flask_restplus import Namespace, Resource

import tipi_tasks
from tipi_backend.api.business import get_tags
from tipi_backend.api.endpoints import cache, limiter
from tipi_backend.api.parsers import parser_tagger
from tipi_backend.settings import Config


log = logging.getLogger(__name__)

ns = Namespace('tagger', description='Operations related to tag texts using our knowledge base')


@ns.route('/')
@ns.expect(parser_tagger)
class TaggerExtractor(Resource):
    decorators = [
        limiter.limit('100/hour', methods=['POST'])
    ]


    def post(self):
        """Returns a list of topics and tags matching the text."""
        try:
            cache_key = Config.CACHE_TAGS
            tags = cache.get(cache_key)
            if tags is None:
                tags = get_tags()
                cache.set(cache_key, tags, timeout=5*60)
            tags = codecs.encode(pickle.dumps(tags), "base64").decode()
            tipi_tasks.init()
            text = ''
            if 'text' in request.form and request.form['text']:
                text = request.form['text']
            else:
                if 'file' in request.files:
                    file_input = request.files['file']
                    with tempfile.NamedTemporaryFile(prefix='tipiscanner_', suffix=splitext(file_input.filename)[1]) as f:
                        f.write(file_input.stream.read())
                        text = process(f.name).decode('utf-8').strip()
                        f.close()
                    if not text:
                        abort(400, "Error al obtener el texto del fichero proporcionado. Pruebe con otro fichero.")
            text_length = len(text.split())

            if text_length >= Config.TAGGER_MAX_WORDS:
                task = tipi_tasks.tagger.extract_tags_from_text.apply_async((text, tags))
                eta_time = int((text_length / 1000) * 4)
                task_id = task.id
                result = {
                        'status': 'PROCESSING',
                        'task_id': task_id,
                        'estimated_time': eta_time
                        }
            else:
                result = tipi_tasks.tagger.extract_tags_from_text(text, tags)
            return result
        except Exception as e:
            if hasattr(e, 'code') and hasattr(e, 'description'):
                abort(e.code, e.description)
            else:
                abort(500, "Internal server error")


@ns.route('/result/<id>')
@ns.param(name='id', description='Task id', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Task not found.')
class TaggerResult(Resource):

    def get(self, id):
        """Returns tagging task's result"""
        tipi_tasks.init()
        return tipi_tasks.tagger.check_status_task(id)
