# -*- coding: utf-8 -*-

from django import contrib
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from dashboard.models import Profile


class ProfileInline(contrib.admin.TabularInline):
    model = Profile


UserAdmin.inlines = (ProfileInline, )

contrib.admin.site.unregister(User)
contrib.admin.site.register(User, UserAdmin)
