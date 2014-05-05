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

from manager.mancelery import celery


@celery.task
def async_instance_operation(operation_id, instance_pk, activity_pk, **kwargs):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(pk=instance_pk)
    operation = getattr(instance, operation_id)
    activity = InstanceActivity.objects.get(pk=activity_pk)

    # save async task UUID to activity
    activity.task_uuid = async_instance_operation.request.id
    activity.save()

    return operation._exec_op(activity=activity, **kwargs)


@celery.task
def async_node_operation(operation_id, node_pk, activity_pk, **kwargs):
    from vm.models import Node, NodeActivity
    node = Node.objects.get(pk=node_pk)
    operation = getattr(node, operation_id)
    activity = NodeActivity.objects.get(pk=activity_pk)

    # save async task UUID to activity
    activity.task_uuid = async_node_operation.request.id
    activity.save()

    return operation._exec_op(activity=activity, **kwargs)
