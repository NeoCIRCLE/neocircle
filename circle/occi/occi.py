from django.contrib.auth.models import User
from django.template.loader import render_to_string

from vm.models import Instance, Lease
from vm.models.common import ARCHITECTURES
from vm.models.instance import ACCESS_METHODS

OCCI_ADDR = "http://localhost:8080/"


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


class Resource(Entity):
    def __init__(self, id, title, kind, summary, links):
        super(Resource, self).__init__(id, title, kind)
        self.summary = summary
        self.links = links


class Compute(Resource):
    # TODO better init, for new resources

    def __init__(self, instance=None, attrs=None, **kwargs):
        self.attrs = {}
        if instance:
            self.location = "%svm/%d/" % (OCCI_ADDR, instance.pk)
            self.instance = instance
            self.init_attrs()
        elif attrs:
            self.attrs = attrs
            self._create_object()

    translate = {
        'occi.core.id': "id",
        'occi.compute.architecture': "arch",
        'occi.compute.cores': "num_cores",
        'occi.compute.hostname': "short_hostname",
        'occi.compute.speed': "priority",
        'occi.compute.memory': "ram_size",
    }

    translate_arch = {

    }

    def _create_object(self):
        params = {}
        for a in self.attrs:
            t = a.split("=")
            params[self.translate.get(t[0])] = t[1]

        params['lease'] = Lease.objects.all()[0]
        params['priority'] = 10
        params['max_ram_size'] = params['ram_size']
        params['system'] = ""
        params['pw'] = "killmenow"
        params['arch'] = (ARCHITECTURES[0][0] if "64" in params['arch'] else
                          ARCHITECTURES[1][0])
        params['access_method'] = ACCESS_METHODS[0][0]
        params['owner'] = User.objects.get(username="test")
        params['name'] = "from occi yo"
        i = Instance.create(params=params, disks=[], networks=[],
                            req_traits=[], tags=[])
        self.location = "%svm/%d/" % (OCCI_ADDR, i.pk)

    def render_location(self):
        return "%s" % self.location

    def render_body(self):
        kind = COMPUTE_KIND
        return render_to_string("occi/compute.html", {
            'kind': kind,
            'attrs': self.attrs,
        })

    def init_attrs(self):
        for k, v in self.translate.items():
            self.attrs[k] = getattr(self.instance, v, None)


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

OS_TPL_MIXIN = Mixin(
    term="os_tpl",
    scheme="http://schemas.ogf.org/occi/infrastructure#",
    class_="mixin",
    title="os template",
    location="/mixin/os_tpl/",
)
