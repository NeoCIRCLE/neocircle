from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

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
    return HttpResponse(json.dumps(rules), content_type='application/json')

def list_hosts(request):
    hosts = [{
        'id': host.id,
        'reverse': host.reverse,
        'name': host.hostname,
        'ipv4': host.ipv4,
        'pub' : 'foo', #ide kell valami!
        'shared_ip': host.shared_ip,
        'description': host.description,
        'comment': host.comment,
        'location': host.location,
        'vlan': {
            'name': host.vlan.name,
            'id': host.vlan.id
        },
        'owner': {
            'name': str(host.owner),
            'id': host.owner.id
        },
        'created_at': host.created_at.isoformat(),
        'modified_at': host.modified_at.isoformat(),
        'groups': [{
            'name': group.name,
            'id': group.id,
        } for group in host.groups.all()]
    } for host in Host.objects.all()]
    return HttpResponse(json.dumps(hosts), content_type='application/json')

def list_vlans(request):
    vlans = [{
        'id': vlan.id,
        'vid': vlan.vid,
        'name': vlan.name,
        'ipv4': vlan.ipv4+'/'+str(vlan.prefix4),
        'ipv6': vlan.ipv6+'/'+str(vlan.prefix6),
        'nat': vlan.snat_ip,
        'description': vlan.description,
        'domain': {
            'id': vlan.domain.id,
            'name': vlan.domain.name,
        }
    } for vlan in Vlan.objects.all()]
    return HttpResponse(json.dumps(vlans), content_type='application/json')

def list_vlangroups(request):
    vlangroups = [{
        'id': group.id,
        'name': group.name,
        'vlans': [{
            'id': vlan.id,
            'name': vlan.name
        } for vlan in group.vlans.all()],
        'description': group.description,
        'owner': {
            'id': group.owner.id,
            'name': str(group.owner)
        },
        'created_at': group.created_at.isoformat(),
        'modified_at': group.modified_at.isoformat(),
    } for group in VlanGroup.objects.all()]
    return HttpResponse(json.dumps(vlangroups), content_type='application/json')

def list_hostgroups(request):
    groups = [{
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'owner': {
            'id': group.owner.id,
            'name': str(group.owner),
        },
        'created_at': group.created_at.isoformat(),
        'modified_at': group.modified_at.isoformat()
    } for group in Group.objects.all()]
    return HttpResponse(json.dumps(groups), content_type='application/json')

def list_firewalls(request):
    firewalls = [{
        'id': firewall.id,
        'name': firewall.name,
    } for firewall in Firewall.objects.all()]
    return HttpResponse(json.dumps(firewalls), content_type='application/json')

def list_domains(request):
    domains = [{
        'id': domain.id,
        'name': domain.name,
        'created_at': domain.created_at.isoformat(),
        'modified_at': domain.modified_at.isoformat(),
        'ttl': domain.ttl,
        'description': domain.description,
        'owner': {
            'id': domain.owner.id,
            'name': str(domain.owner)
        }
    } for domain in Domain.objects.all()]
    return HttpResponse(json.dumps(domains), content_type='application/json')

def list_records(request):
    records = [{
        'id': record.id,
        'name': record.name,
        'domain': {
            'id': record.domain.id,
            'name': record.domain.name,
        },
        'host': {
            'id': record.host.id,
            'name': record.host.hostname,
        } if record.host else None,
        'type': record.type,
        'address': record.address,
        'ttl': record.ttl,
        'owner': {
            'id': record.owner.id,
            'name': str(record.owner)
        },
        'description': record.description,
        'created_at': record.created_at.isoformat(),
        'modified_at': record.modified_at.isoformat()
    } for record in Record.objects.all()]
    return HttpResponse(json.dumps(records), content_type='application/json')

def list_blacklists(request):
    blacklists = [{
        'id': blacklist.id,
        'host': {
            'id': blacklist.host.id,
            'name': blacklist.host.hostname,
        } if blacklist.host else None,
        'reason': blacklist.reason,
        'snort_message': blacklist.snort_message,
        'type': blacklist.type,
        'created_at': blacklist.created_at.isoformat(),
        'modified_at': blacklist.modified_at.isoformat(),
        'ipv4': blacklist.ipv4
    } for blacklist in Blacklist.objects.all()]
    return HttpResponse(json.dumps(blacklists), content_type='application/json')

def show_rule(request, id):
    rule = get_object_or_404(Rule, id=id)
    rule = {
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
        'direction': {
            'value': rule.direction,
            'choices': Rule._meta.get_field_by_name('direction')[0].choices,
        },
        'proto': {
            'value': rule.proto,
            'choices': Rule._meta.get_field_by_name('proto')[0].choices,
        },
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
        'dport': rule.dport,
        'sport': rule.sport,
        'extra': rule.extra,
        'nat_dport': rule.nat_dport
    }
    return HttpResponse(json.dumps(rule), content_type='application/json')

def autocomplete_vlan(request):
    return HttpResponse(json.dumps([{
        'id': vlan.id,
        'name': vlan.name
        } for vlan in Vlan.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_vlangroup(request):
    return HttpResponse(json.dumps([{
        'id': vlangroup.id,
        'name': vlangroup.name
        } for vlangroup in VlanGroup.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_hostgroup(request):
    return HttpResponse(json.dumps([{
        'id': hostgroup.id,
        'name': hostgroup.name
        } for hostgroup in Group.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_host(request):
    return HttpResponse(json.dumps([{
        'id': host.id,
        'name': host.hostname
        } for host in Host.objects.filter(hostname__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_firewall(request):
    return HttpResponse(json.dumps([{
        'id': firewall.id,
        'name': firewall.name
        } for firewall in Firewall.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_domain(request):
    return HttpResponse(json.dumps([{
        'id': domain.id,
        'name': domain.name
        } for domain in Domain.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')

def autocomplete_record(request):
    return HttpResponse(json.dumps([{
        'id': record.id,
        'name': record.name
        } for record in Record.objects.filter(name__icontains=request.POST['name'])[:5]]), content_type='application/json')
