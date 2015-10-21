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

import autocomplete_light
from django.contrib.auth.models import User
from django.utils.html import escape
from django.utils.translation import ugettext as _

from .views import AclUpdateView
from .models import Profile


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


class AclUserGroupAutocomplete(autocomplete_light.AutocompleteGenericBase):
    search_fields = (
        ('first_name', 'last_name', 'username', 'email', 'profile__org_id'),
        ('name', 'groupprofile__org_id'),
    )
    choice_html_format = (u'<span data-value="%s"><span style="display:none"'
                          u'>%s</span>%s</span>')

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

    def choice_html(self, choice):
        return self.choice_html_format % (
            self.choice_value(choice), self.choice_label(choice),
            self.choice_displayed_text(choice))

    def choices_for_request(self):
        user = self.request.user
        self.choices = (AclUpdateView.get_allowed_users(user),
                        AclUpdateView.get_allowed_groups(user))
        return super(AclUserGroupAutocomplete, self).choices_for_request()

    def autocomplete_html(self):
        html = []

        for choice in self.choices_for_request():
            html.append(self.choice_html(choice))

        if not html:
            html = self.empty_html_format % _('no matches found').capitalize()

        return self.autocomplete_html_format % ''.join(html)


class AclUserAutocomplete(AclUserGroupAutocomplete):
    def choices_for_request(self):
        user = self.request.user
        self.choices = (AclUpdateView.get_allowed_users(user), )
        return super(AclUserGroupAutocomplete, self).choices_for_request()


autocomplete_light.register(AclUserGroupAutocomplete)
autocomplete_light.register(AclUserAutocomplete)
