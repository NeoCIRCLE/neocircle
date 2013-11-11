from django.db.models import TextField

from ..models import AclBase


class TestModel(AclBase):
    normal_field = TextField()

    ACL_LEVELS = (
        ('alfa', 'Alfa'),
        ('bravo', 'Bravo'),
        ('charlie', 'Charlie'),
    )


class Test2Model(AclBase):
    normal2_field = TextField()

    ACL_LEVELS = (
        ('one', 'One'),
        ('two', 'Two'),
        ('three', 'Three'),
    )
