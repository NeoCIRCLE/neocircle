import autocomplete_light
from django.utils.translation import ugettext as _

from .views import AclUpdateView


class AclUserAutocomplete(autocomplete_light.AutocompleteGenericBase):
    search_fields = (
        ('^first_name', 'last_name', 'username', '^email', 'profile__org_id'),
        ('^name', 'groupprofile__org_id'),
    )
    autocomplete_js_attributes = {'placeholder': _("Name of group or user")}

    def choices_for_request(self):
        user = self.request.user
        self.choices = (AclUpdateView.get_allowed_users(user),
                        AclUpdateView.get_allowed_groups(user))
        return super(AclUserAutocomplete, self).choices_for_request()


autocomplete_light.register(AclUserAutocomplete)
