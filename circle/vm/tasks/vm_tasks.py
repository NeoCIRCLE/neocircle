from manager.mancelery import celery


def check_queue(node_hostname, queue_id):
    drivers = ['vmdriver', 'netdriver']
    worker_list = [node_hostname + "." + d for d in drivers]
    queue_name = node_hostname + "." + queue_id
    inspect = celery.control.inspect(worker_list)
    # v is List of List of queues dict
    node_workers = [v for k, v in inspect.active_queues().iteritems()]
    for worker in node_workers:
        for queue in worker:
            if queue['name'] == queue_name:
                return True
    return False


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


@celery.task(name='vmdriver.screenshot')
def screenshot(params):
    pass
