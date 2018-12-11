from tipi_backend.database import db

import itertools
import pcre


class Tag(db.EmbeddedDocument):
    tag = db.StringField()
    subtopic = db.StringField()
    regex = db.StringField()
    shuffle = db.BooleanField()


class Topic(db.Document):
    id = db.StringField(db_field='_id', primary_key=True)
    name = db.StringField()
    description = db.ListField(db.StringField())
    icon = db.StringField()
    tags = db.EmbeddedDocumentListField(Tag)

    meta = {'collection': 'topics'}
    # TODO Add indexes https://mongoengine-odm.readthedocs.io/guide/defining-documents.html#indexes

    @staticmethod
    def get_tags():
        tags = []
        delimiter = '.*'
        for topic in Topic.objects():
            for tag in topic['tags']:
                if tag['shuffle']:
                    for permutation in itertools.permutations(tag['regex'].split(delimiter)):
                        tags.append({
                            'topic': topic['name'],
                            'compiletag': pcre.compile('(?i)' + delimiter.join(permutation)),
                            'tag': tag['tag'],
                            'subtopic': tag['subtopic'],
                        })
                else:
                    tags.append({
                        'topic': topic['name'],
                        'compiletag': pcre.compile('(?i)' + tag['regex']),
                        'tag': tag['tag'],
                        'subtopic': tag['subtopic']
                    })
        return tags