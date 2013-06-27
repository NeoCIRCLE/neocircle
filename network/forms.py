from django.forms import ModelForm
from firewall.models import Host


class HostForm(ModelForm):
    class Meta:
        model = Host
