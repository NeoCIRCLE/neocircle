import autocomplete_light
from django.utils.translation import ugettext as _

from .views import AclUpdateView


class AclUserAutocomplete(autocomplete_light.AutocompleteGenericBase):
    search_fields = (
        ('^first_name', 'last_name', 'username', '^email', 'profile__org_id'),
        ('^name', 'groupprofile__org_id'),
    )
    autocomplete_js_attributes = {'placeholder': _("Name of group or user")}
    choice_html_format = u'<span data-value="%s"><span>%s</span> %s</span>'

    def choice_html(self, choice):
        try:
            name = choice.get_full_name()
        except AttributeError:
            name = _('group')
        if name:
            name = u'(%s)' % name

        return self.choice_html_format % (
            self.choice_value(choice), self.choice_label(choice), name)

    def choices_for_request(self):
        user = self.request.user
        self.choices = (AclUpdateView.get_allowed_users(user),
                        AclUpdateView.get_allowed_groups(user))
        return super(AclUserAutocomplete, self).choices_for_request()


autocomplete_light.register(AclUserAutocomplete)
