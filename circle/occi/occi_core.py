""" Implementation of the OCCI - Core model classes """


from occi_utils import set_optional_attributes, serialize_attributes


class Attribute:
    """ OCCI 1.2 - CORE - Classification - Attribute """

    TYPES = ("Object", "List", "Hash")

    optional_attributes = ("pattern", "default", "description")

    def __init__(self, name, type, mutable, required, **kwargs):
        self.name = name
        self.type = type
        self.mutable = mutable
        self.required = required
        set_optional_attributes(self, self.optional_attributes, kwargs)

    def render_as_json(self):
        json = {"mutable": self.mutable, "required": self.required,
                "type": self.type}
        if hasattr(self, "pattern"):
            json["pattern"] = self.pattern
        if hasattr(self, "default"):
            json["default"] = self.default
        if hasattr(self, "description"):
            json["description"] = self.description
        return json


class Category(object):
    """ OCCI 1.2 - CORE - Classification - Category """

    category_optional_attributes = ("title", "attributes")

    def __init__(self, scheme, term, **kwargs):
        self.scheme = scheme
        self.term = term
        set_optional_attributes(self, self.category_optional_attributes,
                                kwargs)


class Kind(Category):
    """ OCCI 1.2 - CORE - Classification - Kind """

    kind_optional_attributes = ("parent", "actions", "enitities")

    def __init__(self, *args, **kwargs):
        super(Kind, self).__init__(*args, **kwargs)
        set_optional_attributes(self, self.kind_optional_attributes,
                                kwargs)

    def render_as_json(self):
        json = {"term": self.term, "scheme": self.scheme}
        if hasattr(self, "title"):
            json["title"] = self.title
        if hasattr(self, "parent"):
            json["parent"] = self.parent
        if hasattr(self, "location"):
            json["location"] = self.location
        if hasattr(self, "attributes"):
            json["attributes"] = serialize_attributes(self.attributes)
        if hasattr(self, "actions"):
            json["actions"] = serialize_attributes(self.actions)
        return json


class Action(Category):
    """ OCCI 1.2 - CORE - Classification - Action """
    def __init(self, *args, **kwargs):
        super(Action, self).__init__(*args, **kwargs)

    def render_as_json(self):
        json = {"term": self.term, "scheme": self.scheme}
        if hasattr(self, "title"):
            json["title"] = self.title
        if hasattr(self, "attributes"):
            json["attributes"] = serialize_attributes(self.attributes)
        return json


class Mixin(Category):
    """ OCCI 1.2 - CORE - Classification - Mixin """

    mixin_optional_attributes = ("depends", "entities", "applies",
                                 "actions")

    def __init__(self, *args, **kwargs):
        super(Mixin, self).__init__(*args, **kwargs)
        set_optional_attributes(self, self.mixin_optional_attributes,
                                kwargs)

    def render_as_json(self):
        json = {"term": self.term, "scheme": self.scheme,
                "attributes": self.attributes, "actions": self.actions}
        if hasattr(self, "title"):
            json["title"] = self.title
        if hasattr(self, "location"):
            json["location"] = self.location
        if hasattr(self, "depends"):
            json["depends"] = self.depends
        if hasattr(self, "applies"):
            json["applies"] = self.applies
        return json


class Entity(object):
    """ OCCI 1.2 - CORE - Base Types - Entity """

    entity_optional_attributes = ("mixins", "title")

    def __init__(self, kind, id, **kwargs):
        self.kind = kind
        self.id = id
        set_optional_attributes(self, self.entity_optional_attributes,
                                kwargs)


class Resource(Entity):
    """ OCCI 1.2 - CORE - Base Types - Resource """

    resource_optional_attributes = ("links", "summary")

    def __init__(self, *args, **kwargs):
        super(Resource, self).__init__(*args, **kwargs)
        set_optional_attributes(self, self.resource_optional_attributes,
                                kwargs)

    def render_as_json(self):
        json = {"kind": self.kind, "id": self.id}
        if hasattr(self, "title"):
            json["title"] = self.title
        if hasattr(self, "summary"):
            json["summary"] = self.summary
        if hasattr(self, "attributes"):
            json["attributes"] = self.attributes
        if hasattr(self, "actions"):
            json["actions"] = self.actions
        if hasattr(self, "links"):
            json["links"] = self.links
        if hasattr(self, "mixins"):
            json["mixins"] = self.mixins
        return json


class Link(Entity):
    """ OCCI 1.2 - CORE - Base Types - Link """

    link_optional_attributes = ("target.kind",)

    def __init__(self, source, target, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)
        self.source = source
        self.target = target
        set_optional_attributes(self, self.link_optional_attributes,
                                kwargs)

    def render_as_json(self):
        json = {"kind": self.kind, "id": self.id, "source": self.source,
                "target": self.target}
        if hasattr(self, "mixins"):
            json["mixins"] = self.mixins
        if hasattr(self, "attributes"):
            json["attributes"] = self.attributes
        if hasattr(self, "actions"):
            json["actions"] = self.actions
        if hasattr(self, "title"):
            json["title"] = self.title
        return json


ENTITY_KIND = Kind("http://schemas.ogf.org/occi/core#", "entity",
                   title="Entity")

RESOURCE_KIND = Kind("http://schemas.ogf.org/occi/core#", "resource",
                     title="Resource",
                     parent="http://schemas.ogf.org/occi/core#entity")
