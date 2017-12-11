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

import json
from dal import autocomplete
from django.contrib.auth.models import User
from django.utils.html import escape
from django.utils.translation import ugettext as _
from django.db.models import Q
from django.http import HttpResponse

from ..views import AclUpdateView
from ..models import Profile


def highlight(field, q, none_wo_match=True):
    """
    >>> highlight('<b>Akkount Krokodil', 'kro', False)
    u'&lt;b&gt;Akkount <span class="autocomplete-hl">Kro</span>kodil'
    """

    if not field:
        return None
    try:
        match = field.lower().index(q.lower())
    except ValueError:
        match = None
    if q and match is not None:
        match_end = match + len(q)
        return (escape(field[:match]) +
                '<span class="autocomplete-hl">' +
                escape(field[match:match_end]) +
                '</span>' + escape(field[match_end:]))
    elif none_wo_match:
        return None
    else:
        return escape(field)


class AclUserAutocomplete(autocomplete.Select2ListView):
    search_fields = ('first_name', 'last_name', 'username',
                     'email', 'profile__org_id')

    def filter(self, qs, search_fields):
        if self.q:
            condition = Q()
            for field in search_fields:
                condition |= Q(**{field + '__icontains': unicode(self.q)})
            return list(qs.filter(condition))
        return []

    def get_list(self):
        users = AclUpdateView.get_allowed_users(self.request.user)
        return self.filter(users, self.search_fields)

    def choice_displayed_text(self, choice):
        q = unicode(self.request.GET.get('q', ''))
        name = highlight(unicode(choice), q, False)
        if isinstance(choice, User):
            extra_fields = [highlight(choice.get_full_name(), q, False),
                            highlight(choice.email, q)]
            try:
                extra_fields.append(highlight(choice.profile.org_id, q))
            except Profile.DoesNotExist:
                pass
            return '%s (%s)' % (name, ', '.join(f for f in extra_fields
                                                if f))
        else:
            return _('%s (group)') % name

    def get(self, *args, **kwargs):
        return HttpResponse(json.dumps({
            'results': [dict(id=unicode(r), text=self.choice_displayed_text(r))
                        for r in self.get_list()]
        }), content_type="application/json")


class AclUserGroupAutocomplete(AclUserAutocomplete):
    group_search_fields = ('name', 'groupprofile__org_id')

    def get_list(self):
        groups = AclUpdateView.get_allowed_groups(self.request.user)
        groups = self.filter(groups, self.group_search_fields)
        return super(AclUserGroupAutocomplete, self).get_list() + groups
