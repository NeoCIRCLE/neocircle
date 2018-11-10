# Copyright 2017 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.


""" Implementation of the OCCI - Core model classes """


from occi.utils import set_optional_attributes


class Attribute(object):
    """ OCCI 1.2 - CORE - Classification - Attribute """

    TYPES = ("Object", "List", "Hash")

    optional_attributes = ("pattern", "default", "description")

    def __init__(self, name, type, mutable, required, **kwargs):
        self.name = name
        self.type = type
        self.mutable = mutable
        self.required = required
        set_optional_attributes(self, self.optional_attributes, kwargs)

    def as_dict(self):
        res = {"mutable": self.mutable, "required": self.required,
               "type": self.type}
        if hasattr(self, "pattern"):
            res["pattern"] = self.pattern
        if hasattr(self, "default"):
            res["default"] = self.default
        if hasattr(self, "description"):
            res["description"] = self.description
        return res


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

    kind_optional_attributes = ("parent", "actions", "enitities",
                                "location",)

    def __init__(self, *args, **kwargs):
        super(Kind, self).__init__(*args, **kwargs)
        set_optional_attributes(self, self.kind_optional_attributes,
                                kwargs)

    def as_dict(self):
        res = {"term": self.term, "scheme": self.scheme}
        if hasattr(self, "title"):
            res["title"] = self.title
        if hasattr(self, "parent"):
            res["parent"] = self.parent
        if hasattr(self, "location"):
            res["location"] = self.location
        if hasattr(self, "attributes"):
            res["attributes"] = {}
            for attribute in self.attributes:
                res["attributes"][attribute.name] = (attribute.as_dict())
        if hasattr(self, "actions"):
            res["actions"] = []
            for action in self.actions:
                res["actions"].append(action.scheme + action.term)
        return res


class Action(Category):
    """ OCCI 1.2 - CORE - Classification - Action """

    def __init(self, *args, **kwargs):
        super(Action, self).__init__(*args, **kwargs)

    def as_dict(self):
        res = {"term": self.term, "scheme": self.scheme}
        if hasattr(self, "title"):
            res["title"] = self.title
        if hasattr(self, "attributes"):
            res["attributes"] = {}
            for attribute in self.attributes:
                res["attributes"][attribute.name] = (attribute.as_dict())
        return res


class Mixin(Category):
    """ OCCI 1.2 - CORE - Classification - Mixin """

    mixin_optional_attributes = ("depends", "entities", "applies",
                                 "actions")

    def __init__(self, *args, **kwargs):
        super(Mixin, self).__init__(*args, **kwargs)
        set_optional_attributes(self, self.mixin_optional_attributes,
                                kwargs)

    def as_dict(self):
        res = {"term": self.term, "scheme": self.scheme}
        if hasattr(self, "title"):
            res["title"] = self.title
        if hasattr(self, "location"):
            res["location"] = self.location
        if hasattr(self, "depends"):
            res["depends"] = self.depends
        if hasattr(self, "applies"):
            res["applies"] = self.applies
        if hasattr(self, "attributes"):
            res["attributes"] = {}
            for attribute in self.attributes:
                res["attributes"][attribute.name] = (attribute.as_dict())
        if hasattr(self, "actions"):
            res["actions"] = []
            for action in self.actions:
                res["actions"].append(action.scheme + action.term)
        return res


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
        set_optional_attributes(
            self, self.resource_optional_attributes, kwargs)

    def as_dict(self):
        res = {"kind": self.kind, "id": self.id}
        if hasattr(self, "title"):
            res["title"] = self.title
        if hasattr(self, "summary"):
            res["summary"] = self.summary
        if hasattr(self, "attributes"):
            res["attributes"] = self.attributes
        if hasattr(self, "actions"):
            res["actions"] = self.actions
        if hasattr(self, "links"):
            res["links"] = self.links
        if hasattr(self, "mixins"):
            res["mixins"] = self.mixins
        return res


class Link(Entity):
    """ OCCI 1.2 - CORE - Base Types - Link """

    link_optional_attributes = ("target.kind",)

    def __init__(self, source, target, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)
        self.source = source
        self.target = target
        set_optional_attributes(self, self.link_optional_attributes, kwargs)

    def as_dict(self):
        res = {"kind": self.kind, "id": self.id, "source": self.source,
               "target": self.target}
        if hasattr(self, "mixins"):
            res["mixins"] = self.mixins
        if hasattr(self, "attributes"):
            res["attributes"] = self.attributes
        if hasattr(self, "actions"):
            res["actions"] = self.actions
        if hasattr(self, "title"):
            res["title"] = self.title
        return res
