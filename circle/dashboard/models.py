from django.contrib.auth.models import User
from django.db.models import Model, ForeignKey

from vm.models import Instance


class Favourite(Model):
    instance = ForeignKey(Instance)
    user = ForeignKey(User)
