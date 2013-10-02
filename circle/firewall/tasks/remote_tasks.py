from manager.mancelery import celery


@celery.task(name='firewall.reload_dns')
def reload_dns(data):
    pass


@celery.task(name='firewall.reload_firewall')
def reload_firewall(data4, data6):
    pass


@celery.task(name='firewall.reload_firewall_vlan')
def reload_firewall_vlan(data):
    pass


@celery.task(name='firewall.reload_dhcp')
def reload_dhcp(data):
    pass


@celery.task(name='firewall.reload_blacklist')
def reload_blacklist(data):
    pass


@celery.task(name='firewall.get_dhcp_clients')
def get_dhcp_clients(data):
    pass
