# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

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
    position_left = models.FloatField()
    position_top = models.FloatField()
    anchor_number = models.PositiveSmallIntegerField()

    def __unicode__(self):
        return "%s (%s)" % (self.service.name, self.display_id)


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
        return "%s (%d)" % (self.target.service.name, self.id)
