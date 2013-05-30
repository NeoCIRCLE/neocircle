from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User

from firewall.fw import *
from firewall.models import *

def req_staff(user):
    ''' decorator function for user permission checking '''
    return user.is_staff

def index(request):
    return render(request, 'firewall/index.html')

def map_rule_target(rule):
    ''' get the actual target from rule field (vlan|vlangroup|host|hostgroup|firewall) '''
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
    ''' jsonify the `attr` attribute of `entity` '''
    # an objects name usually is in the `name` attribute, but not always (thanks bd!), so put here the exceptions
    common_names = {
        'host': 'hostname',
        'owner': 'username',}
    try:
        # return something that can be converted to JSON, based on the `attr` field type
        return {
            # if `attr` is an entity, parse its name&id
            'ForeignKey': lambda entity: {
                'id': entity.id,
                'name': getattr(entity, common_names[attr] if attr in common_names.keys() else 'name')
            } if entity else None,
            # if `attr` is a date, format it with isoformat
            'DateTimeField': lambda entity: entity.isoformat(),
            # if `attr` is a Crazy ManyToMany field, fetch all objects, and get their name&id
            'ManyToManyField': lambda field: [{
                'id': entity.id,
                'name': getattr(entity, common_names[attr] if attr in common_names.keys() else 'name')
            } for entity in field.all()]
        }[entity._meta.get_field_by_name(attr)[0].__class__.__name__](getattr(entity, attr))
    except Exception as e:
        # if `attr` is something else, we hope it can be converted to JSON
        return getattr(entity, attr)

def make_entity_lister(entity_type, mapping):
    ''' makes a function that lists the given entities '''
    def jsonify(entity):
        ''' jsonify one entity '''
        result = {}
        for attr in mapping:
            # if `attr` is a tuple, the first element is the key in the JSON, the second is a function that calculates the value
            if type(attr) is tuple:
                result[attr[0]] = attr[1](entity)
            else:
                # if `attr` is just a string, the try to jsonify the corresponding model attribute
                result[attr] = json_attr(entity, attr)
        return result

    def entity_lister(request):
        ''' jsonify all objects of the given model type '''
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


def show_rule(request, id=None):
    try:
        rule = Rule.objects.get(id=id)
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
    except:
        rule = {
            'id': None,
            'target': { 'id': None, 'name': None, 'type': None },
            'type': None,
            'direction': {
                'value': None,
                'choices': Rule._meta.get_field_by_name('direction')[0].choices,
            },
            'proto': {
                'value': None,
                'choices': Rule._meta.get_field_by_name('proto')[0].choices,
            },
            'owner': {
                'id': None,
                'name': None,
            },
            'foreignNetwork': { 'name': None, 'id': None },
            'created_at': None,
            'modified_at': None,
            'nat': False,
            'accept': False,
            'description': '',
            'dport': None,
            'sport': None,
            'extra': '',
            'nat_dport': None,
        }
    return HttpResponse(json.dumps(rule), content_type='application/json')


def show_host(request, id=None):
    try:
        host = Host.objects.get(id=id)
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
    except:
        host = {
            'id': None,
            'reverse': None,
            'name': None,
            'mac': None,
            'ipv4': None,
            'ipv6': None,
            'pub_ipv4': None,
            'shared_ip': False,
            'description': '',
            'comment': '',
            'location': '',
            'vlan': {
                'name': None,
            },
            'owner': {
                'name': None,
            },
            'created_at': None,
            'modified_at': None,
            'groups': [],
            'rules': []
        }
    return HttpResponse(json.dumps(host), content_type='application/json')


def show_vlan(request, id=None):
    try:
        vlan = Vlan.objects.get(id=id)
        vlan = {
            'id': vlan.id,
            'vid': vlan.vid,
            'name': vlan.name,
            'ipv4': vlan.ipv4+'/'+str(vlan.prefix4),
            'ipv6': vlan.ipv6+'/'+str(vlan.prefix6),
            'net4': vlan.net4+'/'+str(vlan.prefix4),
            'net6': vlan.net6+'/'+str(vlan.prefix6),
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
            } for rule in vlan.rules.all()],
            'vlans': [{
                'id': vlan.id,
                'name': vlan.name,
            } for vlan in vlan.snat_to.all()]
        }
    except:
        vlan = {
            'id': None,
            'vid': None,
            'name': None,
            'ipv4': None,
            'ipv6': None,
            'nat': '',
            'description': '',
            'comment': '',
            'reverse_domain': '',
            'dhcp_pool': '',
            'interface': '',
            'created_at': None,
            'modified_at': None,
            'owner': {
                'name': None,
            },
            'domain': {
                'name': None,
            },
            'rules': [],
            'vlans': []
        }
    return HttpResponse(json.dumps(vlan), content_type='application/json')


def show_vlangroup(request, id=None):
    try:
        group = VlanGroup.objects.get(id=id)
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
    except:
        group = {
            'id': None,
            'name': None,
            'vlans': [],
            'description': '',
            'owner': {
                'name': None
            },
            'created_at': None,
            'modified_at': None,
            'rules': []
        }
    return HttpResponse(json.dumps(group), content_type='application/json')


def show_hostgroup(request, id=None):
    try:
        group = Group.objects.get(id=id)
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
    except:
        group = {
            'id': None,
            'name': None,
            'description': '',
            'owner': {
                'name': None,
            },
            'created_at': None,
            'modified_at': None,
            'hosts': [],
            'rules': []
        }
    return HttpResponse(json.dumps(group), content_type='application/json')

def show_record(request, id=None):
    try:
        record = Record.objects.get(id=id)
        record = {
            'id': record.id,
            'name': record.name,
            'domain': {
                'id': record.domain.id,
                'name': record.domain.name
            },
            'host': {
                'id': record.host.id,
                'name': record.host.hostname
            } if record.host else None,
            'type': record.type,
            'address': record.address,
            'ttl': record.ttl,
            'owner': {
                'id': record.owner.id,
                'name': record.owner.username
            },
            'description': record.description,
            'created_at': record.created_at.isoformat(),
            'modified_at': record.modified_at.isoformat(),
        }
    except:
        record = {
            'id': None,
            'name': None,
            'domain': {
                'name': None
            },
            'host': {
                'name': None
            },
            'type': None,
            'address': None,
            'ttl': None,
            'owner': {
                'name': None
            },
            'description': '',
            'created_at': None,
            'modified_at': None,
        }
    return HttpResponse(json.dumps(record), content_type='application/json')

def show_domain(request, id=None):
    try:
        domain = Domain.objects.get(id=id)
        domain = {
            'id': domain.id,
            'name': domain.name,
            'owner': {
                'id': domain.owner.id,
                'name': domain.owner.username,
            },
            'created_at': domain.created_at.isoformat(),
            'modified_at': domain.modified_at.isoformat(),
            'ttl': domain.ttl,
            'description': domain.description
        }
    except:
        domain = {
            'id': None,
            'name': None,
            'owner': {
                'name': None,
            },
            'created_at': None,
            'modified_at': None,
            'ttl': None,
            'description': ''
        }
    return HttpResponse(json.dumps(domain), content_type='application/json')

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
            'owner': make_autocomplete(User, 'username')
        }[entity](request)
    except Exception as e:
        return HttpResponse('>:-3'+str(e), status=500)


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
    if 'id' in data and data['id']:
        rule = get_object_or_404(Rule, id=data['id'])
    else:
        rule = Rule()
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
    rule.r_type = data['target']['type']
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
    return HttpResponse(rule.id)

@user_passes_test(req_staff)
def save_host(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        host = get_object_or_404(Host, id=data['id'])
    else:
        host = Host()
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
    for group in data['groups']:
        try:
            if '__destroyed' in group and group['__destroyed']:
                group_object = Group.objects.get(name = group['name'])
                host.groups.remove(group_object)
            elif '__created' in group and group['__created']:
                group_object = Group.objects.get(name = group['name'])
                host.groups.add(group_object)
        except Exception as e:
            errors['groups'] = ('Group with the name "%(name)s" does not exists!') % {
                'name': group['name']
            }
    try:
        host.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    host.save()
    return HttpResponse(host.id)

@user_passes_test(req_staff)
def save_vlan(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        vlan = get_object_or_404(Vlan, id=data['id'])
    else:
        vlan = Vlan()
    errors = {}
    vlan.vid = data['vid']
    vlan.name = data['name']
    vlan.ipv4 = data['ipv4'].split('/')[0]
    vlan.net4 = data['net4'].split('/')[0]
    vlan.prefix4 = data['ipv4'].split('/')[1]
    vlan.ipv6 = data['ipv6'].split('/')[0]
    vlan.net6 = data['net6'].split('/')[0]
    vlan.prefix6 = data['ipv6'].split('/')[1]
    if data['ipv4'].split('/')[1] != data['net4'].split('/')[1]:
        errors['ipv4'] = 'Netmask legth should be equal!'
        errors['net4'] = 'Netmask legth should be equal!'
    if data['ipv6'].split('/')[1] != data['net6'].split('/')[1]:
        errors['ipv6'] = 'Netmask legth should be equal!'
        errors['net6'] = 'Netmask legth should be equal!'
    vlan.snat_ip = data['nat']
    vlan.description = data['description']
    vlan.comment = data['comment']
    vlan.reverse_domain = data['reverse_domain']
    vlan.dhcp_pool = data['dhcp_pool']
    vlan.interface = data['interface']
    set_field(vlan, 'owner', errors, username=data['owner']['name'])
    set_field(vlan, 'domain', errors, name=data['domain']['name'])
    for group in data['vlans']:
        try:
            if '__destroyed' in group and group['__destroyed']:
                nat_to = Vlan.objects.get(name = group['name'])
                vlan.snat_to.remove(nat_to)
            elif '__created' in group and group['__created']:
                nat_to = Vlan.objects.get(name = group['name'])
                vlan.snat_to.add(nat_to)
        except Exception as e:
            errors['vlans'] = ('Vlan with the name "%(name)s" does not exists!') % {
                'name': group['name']
            }
    try:
        vlan.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    vlan.save()
    return HttpResponse(vlan.id)

@user_passes_test(req_staff)
def save_vlangroup(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        vlangroup = get_object_or_404(VlanGroup, id=data['id'])
    else:
        vlangroup = VlanGroup()
    errors = {}
    vlangroup.name = data['name']
    vlangroup.description = data['description']
    for vlan in data['vlans']:
        try:
            if '__destroyed' in vlan and vlan['__destroyed']:
                vlan_obj = Vlan.objects.get(name = vlan['name'])
                vlangroup.vlans.remove(vlan_obj)
            elif '__created' in vlan and vlan['__created']:
                vlan_obj = Vlan.objects.get(name = vlan['name'])
                vlangroup.vlans.add(vlan_obj)
        except Exception as e:
            errors['vlans'] = ('Vlan with the name "%(name)s" does not exists!') % {
                'name': vlan['name']
            }
    set_field(vlangroup, 'owner', errors, username=data['owner']['name'])
    try:
        vlangroup.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    vlangroup.save()
    return HttpResponse(vlangroup.id)

@user_passes_test(req_staff)
def save_hostgroup(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        hostgroup = get_object_or_404(Group, id=data['id'])
    else:
        hostgroup = Group()
    errors = {}
    hostgroup.name = data['name']
    hostgroup.description = data['description']
    set_field(hostgroup, 'owner', errors, username=data['owner']['name'])
    try:
        hostgroup.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    hostgroup.save()
    return HttpResponse(hostgroup.id)

@user_passes_test(req_staff)
def save_domain(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        domain = get_object_or_404(Domain, id=data['id'])
    else:
        domain = Domain()
    errors = {}
    domain.name = data['name']
    domain.ttl = data['ttl']
    domain.description = data['description']
    set_field(domain, 'owner', errors, username=data['owner']['name'])
    try:
        domain.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    domain.save()
    return HttpResponse(domain.id)

@user_passes_test(req_staff)
def save_record(request):
    data = json.loads(request.body)
    if 'id' in data and data['id']:
        record = get_object_or_404(Record, id=data['id'])
    else:
        record = Record()
    errors = {}
    record.name = data['name']
    record.ttl = data['ttl']
    record.description = data['description']
    record.type = data['type']
    record.address = data['address']
    set_field(record, 'owner', errors, username=data['owner']['name'])
    set_field(record, 'domain', errors, name=data['domain']['name'])
    try:
        record.full_clean()
    except Exception as e:
        errors = dict(errors.items() + e.message_dict.items())
    if len(errors) > 0:
        return HttpResponse(json.dumps(errors), content_type='application/json', status=400)
    record.save()
    return HttpResponse(record.id)

@user_passes_test(req_staff)
def delete_entity(request, name, id):
    model = {
        'rules': Rule,
        'hosts': Host,
        'hostgroups': Group,
        'vlans': Vlan,
        'vlangroups': VlanGroup,
        'firewalls': Firewall,
        'domains': Domain,
        'records': Record,
        'blacklists': Blacklist
    }[name]
    model.objects.get(id=id).delete()
    return HttpResponse('KTHXBYE')
