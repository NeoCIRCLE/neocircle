from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User

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
        'pub': 'foo',  # ide kell valami!
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


def show_host(request, id):
    host = get_object_or_404(Host, id=id)
    host = {
        'id': host.id,
        'reverse': host.reverse,
        'name': host.hostname,
        'mac': host.mac,
        'ipv4': host.ipv4,
        'ipv6': host.ipv6,
        'pub_ipv4': host.pub_ipv4,
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
        } for group in host.groups.all()],
        'rules': [{
            'id': rule.id,
            'direction': rule.get_direction_display(),
            'proto': rule.proto,
            'owner': {
                'id': rule.owner.id,
                'name': str(rule.owner),
            },
            'accept': rule.accept,
            'nat': rule.nat
        } for rule in host.rules.all()]
    }
    return HttpResponse(json.dumps(host), content_type='application/json')


def show_vlan(request, id):
    vlan = get_object_or_404(Vlan, id=id)
    vlan = {
        'id': vlan.id,
        'vid': vlan.vid,
        'name': vlan.name,
        'ipv4': vlan.ipv4+'/'+str(vlan.prefix4),
        'ipv6': vlan.ipv6+'/'+str(vlan.prefix6),
        'nat': vlan.snat_ip,
        'description': vlan.description,
        'comment': vlan.comment,
        'reverse_domain': vlan.reverse_domain,
        'dhcp_pool': vlan.dhcp_pool,
        'interface': vlan.interface,
        'created_at': vlan.created_at.isoformat(),
        'modified_at': vlan.modified_at.isoformat(),
        'owner': {
            'name': str(vlan.owner),
            'id': vlan.owner.id
        } if vlan.owner else None,
        'domain': {
            'id': vlan.domain.id,
            'name': vlan.domain.name,
        },
        'rules': [{
            'id': rule.id,
            'direction': rule.get_direction_display(),
            'proto': rule.proto,
            'owner': {
                'id': rule.owner.id,
                'name': str(rule.owner),
            },
            'accept': rule.accept,
            'nat': rule.nat
        } for rule in vlan.rules.all()]
    }
    return HttpResponse(json.dumps(vlan), content_type='application/json')


def show_vlangroup(request, id):
    group = get_object_or_404(VlanGroup, id=id)
    group = {
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
        'rules': [{
            'id': rule.id,
            'direction': rule.get_direction_display(),
            'proto': rule.proto,
            'owner': {
                'id': rule.owner.id,
                'name': str(rule.owner),
            },
            'accept': rule.accept,
            'nat': rule.nat
        } for rule in group.rules.all()]
    }
    return HttpResponse(json.dumps(group), content_type='application/json')


def show_hostgroup(request, id):
    group = get_object_or_404(Group, id=id)
    group = {
        'id': group.id,
        'name': group.name,
        'description': group.description,
        'owner': {
            'id': group.owner.id,
            'name': str(group.owner),
        },
        'created_at': group.created_at.isoformat(),
        'modified_at': group.modified_at.isoformat(),
        'hosts': [{
            'id': host.id,
            'name': host.hostname
        } for host in group.host_set.all()],
        'rules': [{
            'id': rule.id,
            'direction': rule.get_direction_display(),
            'proto': rule.proto,
            'owner': {
                'id': rule.owner.id,
                'name': str(rule.owner),
            },
            'accept': rule.accept,
            'nat': rule.nat
        } for rule in group.rules.all()]
    }
    return HttpResponse(json.dumps(group), content_type='application/json')


def make_autocomplete(entity, name='name'):
    def autocomplete(request):
        return HttpResponse(json.dumps([{
            'id': object.id,
            'name': getattr(object, name)
        } for object in entity.objects.filter(**{
            name+'__icontains': request.POST['name']
        })[:5]]), content_type='application/json')
    return autocomplete


def autocomplete(request, entity):
    try:
        return {
            'vlan': make_autocomplete(Vlan),
            'vlangroup': make_autocomplete(VlanGroup),
            'host': make_autocomplete(Host, 'hostname'),
            'hostgroup': make_autocomplete(Group),
            'firewall': make_autocomplete(Firewall),
            'domain': make_autocomplete(Domain),
            'record': make_autocomplete(Record),
        }[entity](request)
    except Exception as e:
        return HttpResponse('>:-3', status=500)


def set_field(object, attr, errors, **kwargs):
    try:
        model = getattr(object.__class__, attr).field.rel.to
        setattr(object, attr, model.objects.get(**kwargs))
    except Exception as e:
        errors[attr] = ('%(model)s with the name "%(name)s" does not exists!') % {
                'model': model.__name__,
                'name': kwargs.values()[0]
            }

def save_rule(request):
    data = json.loads(request.body)
    if data['id']:
        rule = get_object_or_404(Rule, id=data['id'])
    else:
        rule = Rule.objects.create()
    errors = {}
    rule.direction = data['direction']['value']
    rule.description = data['description']
    rule.dport = data['dport']
    rule.sport = data['sport']
    rule.proto = data['proto']['value']
    rule.extra = data['extra']
    rule.accept = data['accept']
    rule.nat = data['nat']
    rule.nat_dport = data['nat_dport']
    set_field(rule, 'owner', errors, username=data['owner']['name'])
    for attr in ['host', 'hostgroup', 'vlan', 'vlangroup', 'firewall']:
        searchBy = 'name' if attr != 'host' else 'hostname'
        if data['target']['type'] == attr:
            set_field(rule, attr, errors, **{searchBy: data['target']['name']})
        else:
            setattr(rule, attr, None)
    set_field(rule, 'foreign_network', errors, name=data['foreignNetwork']['name'])
    try:
        rule.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    rule.save()
    return HttpResponse('KTHXBYE')
