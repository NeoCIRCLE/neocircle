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

from celery.contrib.abortable import AbortableTask
from manager.mancelery import celery


@celery.task(base=AbortableTask, bind=True)
def abortable_async_instance_operation(task, operation_id, instance_pk,
                                       activity_pk, allargs, auxargs):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(pk=instance_pk)
    operation = getattr(instance, operation_id)
    activity = InstanceActivity.objects.get(pk=activity_pk)

    # save async task UUID to activity
    activity.task_uuid = task.request.id
    activity.save()

    allargs['activity'] = activity
    allargs['task'] = task

    return operation._exec_op(allargs, auxargs)


@celery.task(base=AbortableTask, bind=True)
def abortable_async_node_operation(task, operation_id, node_pk, activity_pk,
                                   allargs, auxargs):
    from vm.models import Node, NodeActivity
    node = Node.objects.get(pk=node_pk)
    operation = getattr(node, operation_id)
    activity = NodeActivity.objects.get(pk=activity_pk)

    # save async task UUID to activity
    activity.task_uuid = task.request.id
    activity.save()

    allargs['activity'] = activity
    allargs['task'] = task

    return operation._exec_op(allargs, auxargs)
