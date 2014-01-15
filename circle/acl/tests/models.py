from django.db.models import TextField, ForeignKey
from django.contrib.auth.models import User

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
    owner = ForeignKey(User, null=True)

    ACL_LEVELS = (
        ('one', 'One'),
        ('two', 'Two'),
        ('three', 'Three'),
    )
