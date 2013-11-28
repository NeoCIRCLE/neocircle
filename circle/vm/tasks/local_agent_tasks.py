from manager.mancelery import celery
from vm.tasks.agent_tasks import (restart_networking, change_password,
                                  set_time, set_hostname)
import time


@celery.task
def agent_started(vm):
    from vm.models import Instance, instance_activity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))

    with instance_activity(code_suffix='agent', instance=instance) as act:
        with act.sub_activity('starting'):
            queue = "%s.agent" % instance.node.host.hostname
            print queue
            restart_networking.apply_async(queue=queue,
                                           args=(vm, ))
            change_password.apply_async(queue=queue,
                                        args=(vm, instance.pw))
            set_time.apply_async(queue=queue,
                                 args=(vm, time.time()))
            set_hostname.apply_async(queue=queue,
                                     args=(vm, instance.primary_host.hostname))


@celery.task
def agent_stopped(vm):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    qs = InstanceActivity.objects.filter(instance=instance,
                                         activity_code='vm.Instance.agent')
    act = qs.latest('id')
    with act.sub_activity('stopping'):
        pass


@celery.task
def agent_ok(vm):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    qs = InstanceActivity.objects.filter(instance=instance,
                                         activity_code='vm.Instance.agent')
    act = qs.latest('id')
    with act.sub_activity('ok'):
        pass
