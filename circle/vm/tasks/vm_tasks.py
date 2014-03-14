from django.core.cache import cache
from logging import getLogger

from manager.mancelery import celery

logger = getLogger(__name__)


def check_queue(node_hostname, queue_id):
    """True if the queue is alive.

    Example: check_queue('node01', 'vm'):
    :param node_hostname: Short hostname of the node.
    :param queue_id: Queue identifier (eg. vm).
    """
    drivers = ['vmdriver', 'netdriver', 'agentdriver']
    # worker_list = [node_hostname + "." + d for d in drivers]
    queue_name = node_hostname + "." + queue_id
    active_queues = get_queues()
    if active_queues is None:
        return False
    # v is List of List of queues dict
    node_workers = [v for k, v in active_queues.iteritems()]
    for worker in node_workers:
        for queue in worker:
            if queue['name'] == queue_name:
                return True
    return False

def get_queues():
    """Get active celery queues.

    Result is cached for 10 seconds!
    """
    key = __name__ + u'queues'
    result = cache.get(key)
    if result is None:
        inspect = celery.control.inspect()
        inspect.timeout = 0.1
        result = inspect.active_queues()
        logger.debug('Queue list of length %d cached.', len(result))
        cache.set(key, result, 10)
    return result




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
