from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User

from firewall.fw import *
from firewall.models import *

def req_staff(user):
    return user.is_staff

def index(request):
    return render(request, 'firewall/index.html')

def map_rule_target(rule):
    return {
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
    }

def json_attr(entity, attr):
    common_names = {
        'host': 'hostname',
        'owner': 'username',
    }
    try:
        return {
            'ForeignKey': lambda entity: {
                'id': entity.id,
                'name': getattr(entity, common_names[attr] if attr in common_names.keys() else 'name')
            } if entity else None,
            'DateTimeField': lambda entity: entity.isoformat(),
            'ManyToManyField': lambda field: [{
                'id': entity.id,
                'name': getattr(entity, common_names[attr] if attr in common_names.keys() else 'name')
            } for entity in field.all()]
        }[entity._meta.get_field_by_name(attr)[0].__class__.__name__](getattr(entity, attr))
    except Exception as e:
        return getattr(entity, attr)
    return getattr(entity, attr)

def make_entity_lister(entity_type, mapping):
    def jsonify(entity):
        result = {}
        for attr in mapping:
            if type(attr) is tuple:
                result[attr[0]] = attr[1](entity)
            else:
                result[attr] = json_attr(entity, attr)
        return result

    def entity_lister(request):
        return [jsonify(entity) for entity in entity_type.objects.all()]
    return entity_lister

@user_passes_test(req_staff)
def list_entities(request, name):
    return HttpResponse(json.dumps({
        'rules': make_entity_lister(Rule, [
            'id',
            ('target',map_rule_target),
            'r_type',
            ('direction',lambda rule: rule.get_direction_display()),
            'proto',
            'owner',
            'foreign_network',
            'created_at',
            'modified_at',
            'nat',
            'accept',
            'description']),
        'hosts': make_entity_lister(Host, [
            'id',
            'reverse',
            'ipv4',
            'shared_ip',
            'description',
            'comment',
            'location',
            'vlan',
            'owner',
            'created_at',
            'modified_at',
            'groups']),
        'vlans': make_entity_lister(Vlan, [
            'id',
            'vid',
            'name',
            ('ipv4', lambda vlan: vlan.ipv4+'/'+str(vlan.prefix4)),
            ('ipv6', lambda vlan: vlan.ipv6+'/'+str(vlan.prefix6)),
            ('nat', lambda vlan: vlan.snat_ip),
            'description',
            'domain']),
        'vlangroups': make_entity_lister(VlanGroup, [
            'id',
            'name',
            'vlans',
            'description',
            'owner',
            'created_at',
            'modified_at']),
        'hostgroups': make_entity_lister(Group, [
            'id',
            'name',
            'description',
            'owner',
            'created_at',
            'modified_at']),
        'firewalls': make_entity_lister(Firewall, ['id', 'name']),
        'domains': make_entity_lister(Domain, [
            'id',
            'name',
            'created_at',
            'modified_at',
            'ttl',
            'description',
            'owner']),
        'records': make_entity_lister(Record, [
            'id',
            'name',
            'domain',
            'host',
            'type',
            'address',
            'ttl',
            'owner',
            'description',
            'modified_at',
            'created_at']),
        'blacklists': make_entity_lister(Blacklist, [
            'id',
            'host',
            'reason',
            'snort_message',
            'type',
            'created_at',
            'modified_at',
            'ipv4']),
        }[name](request)), content_type='application/json')


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

@user_passes_test(req_staff)
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

@user_passes_test(req_staff)
def save_host(request):
    data = json.loads(request.body)
    if data['id']:
        host = get_object_or_404(Host, id=data['id'])
    else:
        host = Host.objects.create()
    errors = {}
    host.reverse = data['reverse']
    host.hostname = data['name']
    host.mac = data['mac']
    host.ipv4 = data['ipv4']
    host.ipv6 = data['ipv6']
    host.pub_ipv4 = data['pub_ipv4']
    host.shared_ip = data['shared_ip']
    host.description = data['description']
    host.comment = data['comment']
    host.location = data['location']
    set_field(host, 'vlan', errors, name=data['vlan']['name'])
    set_field(host, 'owner', errors, username=data['owner']['name'])
    # todo: group save
    try:
        host.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    host.save()
    return HttpResponse('KTHXBYE')

def save_vlan(request):
    data = json.loads(request.body)
    if data['id']:
        vlan = get_object_or_404(Vlan, id=data['id'])
    else:
        vlan = Vlan.objects.create()
    errors = {}
    vlan.vid = data['vid']
    vlan.name = data['name']
    vlan.ipv4 = data['ipv4'].split('/')[0]
    vlan.prefix4 = data['ipv4'].split('/')[1]
    vlan.ipv6 = data['ipv6'].split('/')[0]
    vlan.prefix6 = data['ipv6'].split('/')[1]
    vlan.snat_ip = data['nat']
    vlan.description = data['description']
    vlan.comment = data['comment']
    vlan.reverse_domain = data['reverse_domain']
    vlan.dhcp_pool = data['dhcp_pool']
    vlan.interface = data['interface']
    set_field(vlan, 'owner', errors, username=data['owner']['name'])
    set_field(vlan, 'domain', errors, name=data['domain']['name'])
    try:
        vlan.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    vlan.save()
    return HttpResponse('KTHXBYE')
