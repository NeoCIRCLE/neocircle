from django.http import HttpResponse
from django.shortcuts import render

from firewall.fw import *
from firewall.models import *

def index(request):
    return render(request, 'firewall/index.html')

def list_rules(request):
    rules = [{
        'id': rule.id,
        'target': {
            'name': rule.vlan.name,
            'id': rule.vlan.id,
            'type': 'vlan',
        } if rule.vlan else {
            'name': rule.vlangroup.name,
            'id': rule.vlangroup.id,
            'type': 'vlangroup',
        } if rule.vlangroup else {
            'name': rule.hostgroup.name,
            'id': rule.hostgroup.id,
            'type': 'hostgroup',
        } if rule.hostgroup else {
            'name': rule.firewall.name,
            'id': rule.firewall.id,
            'type': 'firewall',
        } if rule.firewall else {
            'name': rule.host.hostname,
            'id': rule.host.id,
            'type': 'host',
        },
        'type': rule.r_type,
        'direction': rule.get_direction_display(),
        'proto': rule.proto,
        'owner': {
            'name': str(rule.owner),
            'id': rule.owner.id
        },
        'foreignNetwork': {
            'name': rule.foreign_network.name,
            'id': rule.foreign_network.id,
        },
        'created_at': rule.created_at.isoformat(),
        'modified_at': rule.modified_at.isoformat(),
        'nat': rule.nat,
        'accept': rule.accept,
        'description': rule.description,
    } for rule in Rule.objects.all()]
    return HttpResponse(json.dumps(rules, indent=2), content_type="application/json")

