from manager.mancelery import celery


@celery.task(name='agent.change_password')
def change_password(vm, password):
    pass


@celery.task(name='agent.restart_networking')
def restart_networking(vm):
    pass


@celery.task(name='agent.set_time')
def set_time(vm, time):
    pass


@celery.task(name='agent.set_hostname')
def set_hostname(vm, time):
    pass
