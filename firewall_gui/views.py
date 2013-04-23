from django.http import HttpResponse
from django.shortcuts import render

from firewall.fw import *
from firewall.models import *

def index(request):
    return render(request, 'firewall/index.html')

def list_rules(request):
    rules = [{
        'id': rule.id,
        'vlan': {
            'name': rule.vlan.name,
            'id': rule.vlan.id,
        } if rule.vlan else None,
        'vlangroup': {
            'name': rule.vlangroup.name,
            'id': rule.vlangroup.id,
        } if rule.vlangroup else None,
        'hostgroup': {
            'name': rule.hostgroup.name,
            'id': rule.hostgroup.id,
        } if rule.hostgroup else None,
        'firewall': {
            'name': rule.firewall.name,
            'id': rule.firewall.id,
        } if rule.firewall else None,
        'host': {
            'name': rule.host.hostname,
            'id': rule.host.id,
        } if rule.host else None,
        'type': rule.r_type,
        'direction': rule.get_direction_display(),
        'proto': rule.proto,
        'owner': {
            'name': str(rule.owner),
            'id': rule.owner.id
        },
        'created_at': rule.created_at.isoformat(),
        'modified_at': rule.modified_at.isoformat(),
        'nat': rule.nat,
        'accept': rule.accept,
        'description': rule.description,
    } for rule in Rule.objects.all()]
    return HttpResponse(json.dumps(rules, indent=2), content_type="application/json")

