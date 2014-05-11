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

# -*- coding: utf-8 -*-

from django import contrib
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import User, Group

from dashboard.models import Profile, GroupProfile


class ProfileInline(contrib.admin.TabularInline):
    model = Profile


class GroupProfileInline(contrib.admin.TabularInline):
    model = GroupProfile


UserAdmin.inlines = (ProfileInline, )
GroupAdmin.inlines = (GroupProfileInline, )

contrib.admin.site.unregister(User)
contrib.admin.site.register(User, UserAdmin)
contrib.admin.site.unregister(Group)
contrib.admin.site.register(Group, GroupAdmin)
