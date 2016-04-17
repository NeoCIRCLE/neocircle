""" Implementation of the OCCI - Core model classes """


from occi_utils import set_optional_attributes


class Attribute:
    """ OCCI 1.2 - CORE - Classification - Attribute """

    TYPES = ("Object", "List", "Hash")

    optional_attributes = ("pattern", "default", "description")

    pattern = None
    default = None
    description = None

    def __init__(self, name, type, mutable, required, **kwargs):
        self.name = name
        self.type = type
        self.mutable = mutable
        self.required = required
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Category:
    """ OCCI 1.2 - CORE - Classification - Category """

    optional_attributes = ("title", "attributes")

    title = None
    attributes = ()

    def __init__(self, scheme, term, **kwargs):
        self.scheme = scheme
        self.term = term
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Kind(Category):
    """ OCCI 1.2 - CORE - Classification - Kind """

    optional_attributes = ("parent", "actions", "enitities")

    parent = None
    actions = ()
    entities = ()

    def __init__(self, **kwargs):
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Action(Category):
    """ OCCI 1.2 - CORE - Classification - Kind """
    pass


class Mixin(Category):
    """ OCCI 1.2 - CORE - Classification - Mixin """

    optional_attributes = ("depends", "entities", "applies", "actions")

    depends = ()
    entities = ()
    applies = ()
    actions = ()

    def __init__(self, **kwargs):
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Entity:
    """ OCCI 1.2 - CORE - Base Types - Entity """

    optional_attributes = ("mixins", "title")

    mixins = ()
    title = None

    def __init__(self, kind, id, **kwargs):
        self.kind = kind
        self.id = id
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Resource(Entity):
    """ OCCI 1.2 - CORE - Base Types - Resource """

    optional_attributes = ("links", "summary")

    links = ()
    summary = None

    def __init__(self, **kwargs):
        set_optional_attributes(self, self.optional_attributes, kwargs)


class Link(Entity):
    """ OCCI 1.2 - CORE - Base Types - Link """

    optional_attributes = ("target_kind",)

    target_kind = None

    def __init__(self, source, target, **kwargs):
        self.source = source
        self.target = target
        set_optional_attributes(self, self.optional_attributes, kwargs)
