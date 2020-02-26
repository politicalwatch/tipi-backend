import logging

from flask import request
from flask_restplus import Namespace, Resource

import tipi_tasks
from tipi_backend.api.business import get_tags
from tipi_backend.api.endpoints import cache, limiter
from tipi_backend.api.parsers import parser_labels


log = logging.getLogger(__name__)

ns = Namespace('labels', description='Operations related to label extraction')


@ns.route('/extract')
@ns.expect(parser_labels)
class LabelsExtractor(Resource):
    decorators = [
        limiter.limit('10/hour', methods=['POST'])
    ]
    def post(self):
        """Returns a dictionary of topics and tags matching the text."""
        cache_key = 'tags-for-labeling'
        tags = cache.get(cache_key)
        if tags is None:
            tags = get_tags()
            cache.set(cache_key, tags, timeout=5*60)

        # Necessary because flask-caching add prefix for cache
        cache_key = Config.CACHE.get('CACHE_KEY_PREFIX') + cache_key

        tipi_tasks.init()
        text = request.form['text']
        text_length = len(text.split())

        if text_length >= Config.LABELING_MAX_WORD:
            task = tipi_tasks.labeling.extract_labels_from_text.apply_async((text, None, cache_key))
            eta_time = int((text_length / 1000) * 2)
            task_id = task
            result = Config.TASK_LABELING_TEXT.format(task_id, eta_time)
        else:
            result = tipi_tasks.labeling.extract_labels_from_text(text, tags=tags)
        return result


@ns.route('/result/<id>')
@ns.param(name='id', description='Task id', type=str, required=True, location=['path'], help='Invalid identifier')
@ns.response(404, 'Task not found.')
class LabelResult(Resource):

    def get(self, id):
        """Returns result of a labeling."""
        tipi_tasks.init()
        return tipi_tasks.labeling.check_status_task(id)
