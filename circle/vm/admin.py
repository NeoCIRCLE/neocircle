# Copyright 2014 Budapest University of Technology and Economics (BME IK)
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

from django.contrib import admin

from .models import (Instance, InstanceActivity, InstanceTemplate, Interface,
                     InterfaceTemplate, Lease, NamedBaseResourceConfig, Node,
                     NodeActivity, Trait, Cluster, VMwareVMInstance)


class InstanceActivityAdmin(admin.ModelAdmin):
        exclude = ('parent', )


admin.site.register(Cluster)
admin.site.register(VMwareVMInstance)
admin.site.register(Instance)
admin.site.register(InstanceActivity, InstanceActivityAdmin)
admin.site.register(InstanceTemplate)
admin.site.register(Interface)
admin.site.register(InterfaceTemplate)
admin.site.register(Lease)
admin.site.register(NamedBaseResourceConfig)
admin.site.register(Node)
admin.site.register(NodeActivity)
admin.site.register(Trait)
