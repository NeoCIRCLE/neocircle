from django.contrib import admin

from .models import (Instance, InstanceActivity, InstanceTemplate, Interface,
                     InterfaceTemplate, Lease, NamedBaseResourceConfig, Node,
                     NodeActivity, Trait)


admin.site.register(Instance)
admin.site.register(InstanceActivity)
admin.site.register(InstanceTemplate)
admin.site.register(Interface)
admin.site.register(InterfaceTemplate)
admin.site.register(Lease)
admin.site.register(NamedBaseResourceConfig)
admin.site.register(Node)
admin.site.register(NodeActivity)
admin.site.register(Trait)
