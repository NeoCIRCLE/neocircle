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
