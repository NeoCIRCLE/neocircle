from manager.mancelery import celery


@celery.task(name='vmdriver.create')
def deploy(params):
    pass


@celery.task(name='vmdriver.delete')
def destroy(params):
    pass


@celery.task(name='vmdriver.save')
def sleep(params):
    pass


@celery.task(name='vmdriver.restore')
def wake_up(params):
    pass


@celery.task(name='vmdriver.suspend')
def suspend(params):
    pass


@celery.task(name='vmdriver.resume')
def resume(params):
    pass


@celery.task(name='vmdriver.shutdown')
def shutdown(params):
    pass


@celery.task(name='vmdriver.reset')
def reset(params):
    pass


@celery.task(name='vmdriver.reboot')
def reboot(params):
    pass


@celery.task(name='vmdriver.migrate')
def migrate(params):
    pass


@celery.task(name='vmdriver.domain_info')
def domain_info(params):
    pass


@celery.task(name='vmdriver.list_domains')
def list_domains(params):
    pass


@celery.task(name='vmdriver.list_domains_info')
def list_domains_info(params):
    pass


@celery.task(name='vmdriver.ping')
def ping(params):
    pass


@celery.task(name='vmdriver.get_core_num')
def get_core_num(params):
    pass


@celery.task(name='vmdriver.get_ram_size')
def get_ram_size(params):
    pass

@celery.task(name='vmdriver.get_node_metrics')
def get_node_metrics(params):
    pass

