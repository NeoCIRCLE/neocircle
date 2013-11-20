from manager.mancelery import celery
from vm.models import Node


@celery.task
def update_domain_states():
    nodes = Node.objects.filter(enabled=True).all()
    for node in nodes:
        node.update_vm_states()
