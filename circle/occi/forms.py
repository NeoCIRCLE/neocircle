from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login


class OcciAuthForm(AuthenticationForm):
    def __init__(self, request, *args, **kwargs):
        super(OcciAuthForm, self).__init__(*args, **kwargs)
        self.request = request

    def confirm_login_allowed(self, user):
        super(OcciAuthForm, self).confirm_login_allowed(user)
        login(self.request, user)
