import marshmallow_mongoengine as ma
from tipi_backend.database.models.topic import Topic


class TagsField(ma.fields.Field):
    def _serialize(self, value, attr, obj):
        return [{'subtopic': v['subtopic'], 'tag': v['tag']} for v in value]


class TopicSchema(ma.ModelSchema):
    class Meta:
        model = Topic
        model_skip_values = [None]
        model_fields_kwargs = {
                'description': {'load_only': True},
                'tags': {'load_only': True}
                }


class TopicExtendedSchema(ma.ModelSchema):
    class Meta:
        model = Topic
        model_skip_values = [None]

    tags = TagsField(attribute="tags")
