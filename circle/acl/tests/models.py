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
        ('owner', 'owner'),
    )
