from django.contrib.auth.models import User

from vm.models import Instance, Lease
from vm.models.common import ARCHITECTURES
from vm.models.instance import ACCESS_METHODS


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

        simple_arguments = ["scheme", "class", "title", "rel", "location"]
        for i in simple_arguments:
            if hasattr(self, i):
                ret += ' %s="%s";' % (i, getattr(self, i))

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
        if instance:
            self.location = "http://10.7.0.103:8080/occi/vm/%d" % instance.pk
        elif attrs:
            self.attrs = attrs
            self._create_object()

    translate = {
        'occi.compute.architecture': "arch",
        'occi.compute.cores': "num_cores",
        'occi.compute.hostname': "???",
        'occi.compute.speed': "priority",
        'occi.compute.memory': "ram_size",
    }

    def _create_object(self):
        params = {}
        for a in self.attrs:
            t = a.split("=")
            params[self.translate.get(t[0])] = t[1]

        print params
        params['lease'] = Lease.objects.all()[0]
        params['priority'] = 10
        params['max_ram_size'] = params['ram_size']
        params['system'] = "welp"
        params['pw'] = "killmenow"
        params['arch'] = (ARCHITECTURES[0][0] if "64" in params['arch'] else
                          ARCHITECTURES[1][0])
        params['access_method'] = ACCESS_METHODS[0][0]
        params['owner'] = User.objects.get(username="test")
        params['name'] = "from occi yo"
        i = Instance.create(params=params, disks=[], networks=[],
                            req_traits=[], tags=[])
        self.location = "http://10.7.0.103:8080/occi/vm/%d" % i.pk

    def render_location(self):
        return "X-OCCI-Location: %s" % self.location

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
    location="10.7.0.103:8080/occi/compute/",
)
