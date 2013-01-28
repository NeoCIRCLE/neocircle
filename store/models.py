from django.db import models
from modeldict import ModelDict

class Setting(models.Model):
    key = models.CharField(max_length=32)
    value = models.CharField(max_length=200)
settings = ModelDict(Setting, key='key', value='value', instances=False)
