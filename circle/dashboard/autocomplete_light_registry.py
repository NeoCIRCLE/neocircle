import autocomplete_light
from django.contrib.auth.models import User
from django.utils.html import escape
from django.utils.translation import ugettext as _

from .views import AclUpdateView
from .models import Profile


class AclUserGroupAutocomplete(autocomplete_light.AutocompleteGenericBase):
    search_fields = (
        ('first_name', 'last_name', 'username', 'email', 'profile__org_id'),
        ('name', 'groupprofile__org_id'),
    )
    choice_html_format = (u'<span data-value="%s"><span style="display:none"'
                          u'>%s</span>%s</span>')

    def highlight(self, field, q, none_wo_match=True):
        if not field:
            return None
        try:
            match = field.lower().index(q.lower())
        except ValueError:
            match = None
        if q and match is not None:
            match_end = match + len(q)
            return (escape(field[:match])
                    + '<span class="autocomplete-hl">'
                    + escape(field[match:match_end])
                    + '</span>' + escape(field[match_end:]))
        elif none_wo_match:
            return None
        else:
            return escape(field)

    def choice_displayed_text(self, choice):
        q = unicode(self.request.GET.get('q', ''))
        name = self.highlight(unicode(choice), q, False)
        if isinstance(choice, User):
            extra_fields = [self.highlight(choice.get_full_name(), q, False),
                            self.highlight(choice.email, q)]
            try:
                extra_fields.append(self.highlight(choice.profile.org_id, q))
            except Profile.DoesNotExist:
                pass
            return '%s (%s)' % (name, ', '.join(f for f in extra_fields
                                                if f))
        else:
            return '%s (%s)' % (name, _('group'))

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
