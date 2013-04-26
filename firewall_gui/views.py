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
    return HttpResponse(json.dumps(rules), content_type="application/json")

def list_hosts(request):
    hosts = [{
        "id": host.id,
        "reverse": host.reverse,
        "name": host.hostname,
        "ipv4": host.ipv4,
        "pub" : "foo", #ide kell valami!
        "shared_ip": host.shared_ip,
        "description": host.description,
        "comment": host.comment,
        "location": host.location,
        "vlan": {
            "name": host.vlan.name,
            "id": host.vlan.id
        },
        "owner": {
            "name": str(host.owner),
            "id": host.owner.id
        },
        "created_at": host.created_at.isoformat(),
        "modified_at": host.modified_at.isoformat(),
        "groups": [{
            "name": group.name,
            "id": group.id,
        } for group in host.groups.all()]
    } for host in Host.objects.all()]
    return HttpResponse(json.dumps(hosts), content_type="application/json")
