import re

from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils import timezone

from storage.models import Disk
from vm.models import Instance, InstanceTemplate, Lease
from vm.models.common import ARCHITECTURES
from vm.models.instance import ACCESS_METHODS, pwgen

OCCI_ADDR = "http://localhost:8080/"

X86_ARCH = ARCHITECTURES[1][0]
X64_ARCH = ARCHITECTURES[0][0]

occi_attribute_regex = re.compile(
    '^X-OCCI-Attribute: ?(?P<attribute>[a-zA-Z\.]+)="?(?P<value>[^"]*)"?$')

occi_action_regex = re.compile(
    '^Category: (?P<term>[a-zA-Z]+); ?scheme=".+"; ?class="action"$')

compute_action_to_operation = {
    'stop': {
        'graceful': "shutdown",
        'acpioff': "shutdown",
        'poweroff': "shut_off",
    },
    'restart': {
        'graceful': "restart",
        'warm': "restart",
        'cold': "reset",
    },
    'suspend': {
        'suspend': "sleep",
        'hibernate': "sleep",
    }
}

occi_os_tpl_regex = re.compile(
    '^Category: ?os_tpl_(?P<template_pk>\d+); ?'
    'scheme=".*/infrastructure/os_tpl#"; ?'
    'class="mixin"; ?location=".*"; ?title=".*"$'
)


occi_link_regex = re.compile(
    '^Link: <(?P<link>[a-zA-Z0-9/]+)>; ?'
    '.*$'
)

occi_inline_attribute_regex = '.*%(attribute)s="?(?P<value>[\w/\.:#\-]+)"?.*'

occi_attribute_link_regex = '^/%s/(?P<id>\d+)/?'


class Category():
    """Represents a Category object

    actions needs a list of Actions
    attributes needs a list of Attributes
    """
    optional_arguments = ["title", "rel", "location", "attributes",
                          "actions", "class"]

    def __init__(self, term, scheme, class_, **kwargs):
        # workaround for class named keyword argument
        kwargs['class'] = class_
        self.term = term
        self.scheme = scheme
        self.class_ = class_
        for k, v in kwargs.iteritems():
            if k in self.optional_arguments:
                setattr(self, k, v)

    def render_values(self):
        ret = "%s;" % self.term

        simple_arguments = ["scheme", "class", "title", "rel"]
        for i in simple_arguments:
            if hasattr(self, i):
                ret += ' %s="%s";' % (i, getattr(self, i))

        if hasattr(self, "location"):
            ret += ' location="%s";' % self.location
        if hasattr(self, "attributes"):
            ret += ' attributes="%s";' % " ".join(
                [a.render() for a in self.attributes])
        if hasattr(self, "actions"):
            ret += ' actions="%s";' % " ".join(
                [a.render() for a in self.actions])

        return ret[:-1]  # trailing semicolon


# TODO related, entity_type, entities
class Kind(Category):
    pass


class Mixin(Category):
    pass


class Attribute():
    def __init__(self, name, property=None):
        self.name = name
        self.property = property

    def render(self):
        attr = self.name
        if self.property:
            attr += "{%s}" % self.property
        return attr


class Action(Category):
    def render(self):
        return "%s%s" % (self.scheme, self.term)


class Entity():
    def __init__(self, id, title, kind):
        self.id = id
        self.title = title
        self.kind = kind


class Link(Entity):
    pass


class Resource(Entity):
    def __init__(self, id, title, kind, summary, links):
        super(Resource, self).__init__(id, title, kind)
        self.summary = summary
        self.links = links


class Compute(Resource):
    """ Note: 100 priority = 5 Ghz
    """

    def __init__(self, instance=None, data=None):
        self.attrs = {}
        if instance:
            self.location = "/vm/%d/" % (instance.pk)
            self.instance = instance
            self.init_attrs()

    @classmethod
    def create_object(cls, data):
        # TODO user
        user = User.objects.get(username="test")
        template = None
        attributes = {}
        links = []

        for d in data:
            tmpl = occi_os_tpl_regex.match(d)
            if tmpl:
                pk = tmpl.group("template_pk")
                template = InstanceTemplate.objects.get(pk=pk)

            attr = occi_attribute_regex.match(d)
            if attr:
                attributes[attr.group("attribute")] = attr.group("value")

            link = occi_link_regex.match(d)
            if link:
                links.append(d)

        params = {}
        params['owner'] = user
        title = attributes.get("occi.core.title")
        if title:
            params['name'] = title

        if template:
            inst = Instance.create_from_template(template=template, **params)
        else:
            # trivial
            if "x86" in attributes['occi.compute.architecture']:
                params['arch'] = X86_ARCH
            else:
                params['arch'] = X64_ARCH

            params['num_cores'] = int(attributes['occi.compute.cores'])
            speed = float(attributes['occi.compute.speed'])
            if speed/5.0 > 1:
                priority = 100
            else:
                priority = int(speed/5.0 * 100.0)
            params['priority'] = priority

            memory = float(attributes['occi.compute.memory']) * 1024
            params['ram_size'] = params['max_ram_size'] = int(memory)

            params['pw'] = pwgen()

            # non trivial
            params['system'] = "OCCI Blank Compute"
            params['lease'] = Lease.objects.all()[0]
            params['access_method'] = ACCESS_METHODS[0][0]

            # if no name is given
            if not params.get("name"):
                params['name'] = "Created via OCCI by %s" % user

            inst = Instance.create(params=params, disks=[], networks=[],
                                   req_traits=[], tags=[])

        cls.location = "%svm/%d" % (OCCI_ADDR, inst.pk)
        cls.instance = inst

        cls.create_links(user, links)
        return cls

    @classmethod
    def create_links(cls, user, links):
        storagelinks = []
        for l in links:
            rel = re.match(occi_inline_attribute_regex % {'attribute': "rel"},
                           l)
            if rel and rel.group("value").endswith("#storage"):
                target = re.match(
                    occi_inline_attribute_regex % {
                        'attribute': "occi.core.target"
                    }, l
                ).group("value")
                disk_pk = re.match(occi_attribute_link_regex % "storage",
                                   target).group("id")
                disk = Disk.objects.get(pk=disk_pk)
                storagelinks.append(disk)

        for sl in storagelinks:
            cls.instance.attach_disk(user=user, disk=disk)

    def render_location(self):
        return "%s" % self.location

    def render_body(self):
        kind = COMPUTE_KIND
        mixins = []
        links = []
        if self.instance.template:
            mixins.append(OsTemplate(self.instance.template))

        for d in self.instance.disks.all():
            links.append(StorageLink(self.instance, d))

        return render_to_string("occi/compute.html", {
            'kind': kind,
            'attrs': self.attrs,
            'mixins': mixins,
            'links': links,
        })

    def init_attrs(self):
        translate = {
            'occi.core.id': "id",
            'occi.compute.architecture': "arch",
            'occi.compute.cores': "num_cores",
            'occi.compute.hostname': "short_hostname",
            'occi.compute.speed': "priority",
            'occi.compute.memory': "ram_size",
            'occi.core.title': "name",
        }
        for k, v in translate.items():
            self.attrs[k] = getattr(self.instance, v, None)

        priority = self.instance.priority
        self.attrs['occi.compute.speed'] = priority/100.0 * 5.0

        status = {
            'RUNNING': "active",
            'SUSPENDED': "suspended",
        }
        self.attrs['occi.compute.state'] = status.get(self.instance.status,
                                                      "inactive")

    def trigger_action(self, data):
        method = None
        action_term = None
        for d in data:
            m = occi_attribute_regex.match(d)
            if m:
                attribute = m.group("attribute")
                if attribute == "method":
                    method = m.group("value")

            m = occi_action_regex.match(d)
            if m:
                action_term = m.group("term")

        if action_term == "start":
            if self.instance.status == "SUSPENDED":
                operation = "wake_up"
            else:
                operation = "deploy"
        else:
            action = compute_action_to_operation.get(action_term)
            operation = action.get(method)

        # TODO user
        user = User.objects.get(username="test")
        getattr(self.instance, operation).async(user=user)

    def delete(self):
        # TODO
        user = User.objects.get(username="test")
        self.instance.destroy(user=user)


class OsTemplate(Mixin):
    def __init__(self, template):
        self.term = "os_tpl_%d" % template.pk
        self.title = template.system
        self.scheme = "http://cloud.bme.hu/occi/infrastructure/os_tpl#"
        self.rel = "http://schemas.ogf.org/occi/infrastructure#os_tpl"
        self.location = "/mixin/os_tpl/%s/" % self.term

    def render_location(self):
        return self.location

    def render_body(self):
        return render_to_string("occi/os_tpl.html", {
            'term': self.term,
            'scheme': self.scheme,
            'rel': self.rel,
            'location': self.location,
            'class': "mixin",
            'title': self.title,
        })


class Storage(Resource):

    def __init__(self, disk=None, data=None):
        self.attrs = {}
        if disk:
            self.location = "/disk/%d/" % (disk.pk)
            self.disk = disk
            self.init_attrs()

    @classmethod
    def create_object(cls, data):
        attributes = {}

        for d in data:
            attr = occi_attribute_regex.match(d)
            if attr:
                attributes[attr.group("attribute")] = attr.group("value")

        size = attributes.get("occi.storage.size")
        if not (size and size.isdigit()):
            return None

        name = attributes.get("occi.core.title")
        if not name:
            name = "disk create from OCCI at %s" % timezone.now()

        # TODO user
        user = User.objects.get(username="test")

        params = {
            'user': user,
            'size': int(float(size) * 1024**3),  # GiB to byte
            'type': "qcow2-norm",
            'name': name,
        }

        disk = Disk.create(**params)
        disk.full_clean()

        cls.location = "%sdisk/%d" % (OCCI_ADDR, disk.pk)
        return cls

    def render_location(self):
        return "%s" % self.location

    def render_body(self):
        kind = STORAGE_KIND
        mixins = []

        return render_to_string("occi/storage.html", {
            'kind': kind,
            'attrs': self.attrs,
            'mixins': mixins,
        })

    def init_attrs(self):
        translate = {
            'occi.core.id': "id",
            'occi.storage.size': "size",
            'occi.core.title': "name",
        }
        for k, v in translate.items():
            self.attrs[k] = getattr(self.disk, v, None)

        self.attrs['occi.storage.state'] = "online"
        self.attrs['occi.storage.size'] /= 1024*1024*1024.0

    def trigger_action(self, data):
        method = None
        action_term = None
        for d in data:
            m = occi_attribute_regex.match(d)
            if m:
                attribute = m.group("attribute")
                if attribute == "method":
                    method = m.group("value")

            m = occi_action_regex.match(d)
            if m:
                action_term = m.group("term")

        if action_term == "start":
            if self.instance.status == "SUSPENDED":
                operation = "wake_up"
            else:
                operation = "deploy"
        else:
            action = compute_action_to_operation.get(action_term)
            operation = action.get(method)

        # TODO user
        user = User.objects.get(username="test")
        getattr(self.instance, operation).async(user=user)


class StorageLink(Link):
    def __init__(self, instance=None, disk=None, data=None):
        if instance and disk:
            self.init_attrs(instance, disk)
        elif data:
            pass

    def init_attrs(self, instance, disk):
        self.attrs = {}
        self.attrs['occi.core.id'] = "vm%d_disk%d" % (instance.pk, disk.pk)
        self.attrs['occi.core.target'] = Storage(disk).render_location()
        self.attrs['occi.core.source'] = Compute(instance).render_location()
        # deviceid? mountpoint?
        self.attrs['occi.core.state'] = "active"

        self.instance = instance
        self.disk = disk

    @classmethod
    def create_object(cls, data):
        attributes = {}

        for d in data:
            attr = occi_attribute_regex.match(d)
            if attr:
                attributes[attr.group("attribute")] = attr.group("value")

        source = attributes.get("occi.core.source")
        target = attributes.get("occi.core.target")
        if not (source and target):
            return None

        # TODO user
        user = User.objects.get(username="test")
        g = re.match(occi_attribute_link_regex % "storage", target)
        disk_pk = g.group("id")
        g = re.match(occi_attribute_link_regex % "vm", source)
        vm_pk = g.group("id")

        try:
            vm = Instance.objects.filter(destroyed_at=None).get(pk=vm_pk)
            disk = Disk.objects.filter(destroyed=None).get(pk=disk_pk)
        except (Instance.DoesNotExist, Disk.DoesNotExist):
            return None

        try:
            vm.attach_disk(user=user, disk=disk)
        except:
            pass

        cls.location = "%sstoragelink/%svm_%sdisk" % (OCCI_ADDR, vm_pk,
                                                      disk_pk)
        return cls

    def render_location(self):
        return "/link/storagelink/vm%d_disk%d" % (self.instance.pk,
                                                  self.disk.pk)

    def render_as_link(self):
        kind = STORAGE_LINK_KIND

        return render_to_string("occi/link.html", {
            'kind': kind,
            'location': self.render_location(),
            'target': self.attrs['occi.core.target'],
            'attrs': self.attrs,
        })

    def render_as_category(self):
        kind = STORAGE_LINK_KIND

        return render_to_string("occi/storagelink.html", {
            'kind': kind,
            'attrs': self.attrs,
        })

    def delete(self):
        # TODO
        user = User.objects.get(username="test")

        if self.disk in self.instance.disks.all():
            self.instance.detach_disk(user=user, disk=self.disk)


"""predefined stuffs


storage attributes and actions
    http://ogf.org/documents/GFD.184.pdf 3.3 (page 7)

storagelink attributes
    http://ogf.org/documents/GFD.184.pdf 3.4.2 (page 10)
"""


# compute attributes and actions
# http://ogf.org/documents/GFD.184.pdf 3.1 (page 5)
COMPUTE_ATTRS = [
    Attribute("occi.compute.architecture"),
    Attribute("occi.compute.cores"),
    Attribute("occi.compute.hostname"),
    Attribute("occi.compute.speed"),
    Attribute("occi.compute.memory"),
    Attribute("occi.compute.state", "immutable"),
]

COMPUTE_ACTIONS = [
    Action(
        "start",
        "http://schemas.ogf.org/occi/infrastructure/compute/action#",
        "action",
        title="Start compute resource",
    ),
    Action(
        "stop",
        "http://schemas.ogf.org/occi/infrastructure/compute/action#",
        "action",
        title="Stop compute resource",
        attributes=[Attribute("method")],
    ),
    Action(
        "restart",
        "http://schemas.ogf.org/occi/infrastructure/compute/action#",
        "action",
        title="Restart compute resource",
        attributes=[Attribute("method")],
    ),
    Action(
        "suspend",
        "http://schemas.ogf.org/occi/infrastructure/compute/action#",
        "action",
        title="Suspend compute resource",
        attributes=[Attribute("method")],
    ),
]

COMPUTE_KIND = Kind(
    term="compute",
    scheme="http://schemas.ogf.org/occi/infrastructure#",
    class_="kind",
    title="Compute Resource type",
    rel="http://schemas.ogf.org/occi/core#resource",
    attributes=COMPUTE_ATTRS,
    actions=COMPUTE_ACTIONS,
    location="/compute/",
)


STORAGE_ATTRS = [
    Attribute("occi.storage.architecture"),
    Attribute("occi.storage.state", "immutable"),
]

STORAGE_ACTIONS = [
    Action(
        "resize",
        "http://schemas.ogf.org/occi/infrastructure/storage/action#",
        "action",
        title="Resize disk",
        attributes=[Attribute("size")],
    ),
]

STORAGE_KIND = Kind(
    term="storage",
    scheme="http://schemas.ogf.org/occi/infrastructure#",
    class_="kind",
    title="Storage Resource type",
    rel="http://schemas.ogf.org/occi/core#resource",
    attributes=STORAGE_ATTRS,
    actions=STORAGE_ACTIONS,
    location="/storage/",
)


OS_TPL_MIXIN = Mixin(
    term="os_tpl",
    scheme="http://schemas.ogf.org/occi/infrastructure#",
    class_="mixin",
    title="os template",
    location="/mixin/os_tpl/",
)


LINK_ATTRS = [
    Attribute("occi.core.id", "immutable"),
    Attribute("occi.core.title"),
    Attribute("occi.core.target"),
    Attribute("occi.core.source"),
]

LINK_KIND = Kind(
    term="link",
    scheme="http://schemas.ogf.org/occi/core#",
    class_="kind",
    title="Link",
    rel="http://schemas.ogf.org/occi/core#entity",
    location="/link/",
    attributes=LINK_ATTRS
)


STORAGE_LINK_ATTRS = LINK_ATTRS + [
    Attribute("occi.storagelink.deviceid"),
    Attribute("occi.storagelink.mountpoint"),
    Attribute("occi.core.state", "immutable"),
]

STORAGE_LINK_KIND = Kind(
    term="storagelink",
    scheme="http://schemas.ogf.org/occi/infrastructure#",
    class_="kind",
    title="Storage link",
    rel="http://schemas.ogf.org/occi/core#link",
    location="/link/storagelink/",
    attributes=STORAGE_LINK_ATTRS
)
