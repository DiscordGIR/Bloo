from datetime import datetime

import mongoengine


class Tag(mongoengine.EmbeddedDocument):
    name         = mongoengine.StringField(required=True)
    content      = mongoengine.StringField(required=True)
    added_by_tag = mongoengine.StringField()
    added_by_id  = mongoengine.IntField()
    added_date   = mongoengine.DateTimeField(default=datetime.now)
    use_count    = mongoengine.IntField(default=0)
    image        = mongoengine.FileField(default=None)
