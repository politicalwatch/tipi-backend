from webargs import fields


detail_args = {
        'id': fields.String(required=True,location='view_args')
        }

search_initiatives_args = {
        'topic': fields.String(missing=""),
        'tags': fields.List(fields.Str(), missing=list),
        'author': fields.String(missing=""),
        'startdate': fields.Date(missing=None),
        'enddate': fields.Date(missing=None),
        'place': fields.String(missing=""),
        'reference': fields.String(missing=""),
        'type': fields.String(missing=""),
        'state': fields.String(missing=""),
        'title': fields.String(missing=""),
        }
