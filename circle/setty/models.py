from django.db import models
from django.db.models import Model
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.utils.translation import ugettext_lazy as _
from storage import OverwriteStorage


class Service(Model):
    user = models.ForeignKey(User)
    name = models.TextField(verbose_name="Name")
    status = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class ElementTemplate(Model):
    name = models.CharField(max_length=50)
    logo = models.FileField(upload_to='setty/', storage=OverwriteStorage())
    description = models.TextField()
    parameters = models.TextField()
    compatibles = models.ManyToManyField('self')
    tags = TaggableManager(blank=True, verbose_name=_("tags"))

    def __unicode__(self):
        return self.name


class Element(Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    parameters = models.TextField()
    display_id = models.TextField()
    pos_x = models.PositiveSmallIntegerField()
    pos_y = models.PositiveSmallIntegerField()
    anchors = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return self.service.name + ", id: " + self.display_id


class ElementConnection(Model):
    target = models.ForeignKey(
        Element,
        related_name='target',
        on_delete=models.CASCADE)
    source = models.ForeignKey(
        Element,
        related_name='source',
        on_delete=models.CASCADE)
    source_endpoint = models.TextField()
    target_endpoint = models.TextField()
    parameters = models.TextField()

    def __unicode__(self):
        return self.target.service.name + ", " + str(self.id)
