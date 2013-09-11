from django.contrib import admin

from .models import (Node, InstanceTemplate, InterfaceTemplate, Instance,
                     InstanceActivity, NodeActivity, Lease)


admin.site.register(Node)
admin.site.register(InstanceTemplate)
admin.site.register(InterfaceTemplate)
admin.site.register(Instance)
admin.site.register(InstanceActivity)
admin.site.register(NodeActivity)
admin.site.register(Lease)
