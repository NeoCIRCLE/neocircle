from manager.mancelery import celery


@celery.task
def async_operation(operation_id, instance_pk, activity_pk, **kwargs):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(pk=instance_pk)
    operation = getattr(instance, operation_id)
    activity = InstanceActivity.objects.get(pk=activity_pk)

    # save async task UUID to activity
    activity.task_uuid = async_operation.request.id
    activity.save()

    return operation._exec_op(activity=activity, **kwargs)


@celery.task
def flush(node, user):
    node.flush(task_uuid=flush.request.id, user=user)
