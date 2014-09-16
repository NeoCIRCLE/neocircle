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


@celery.task(name='agent.mount_store')
def mount_store(vm, host, username, password):
    pass


@celery.task(name='agent.cleanup')
def cleanup(vm):
    pass


@celery.task(name='agent.start_access_server')
def start_access_server(vm):
    pass


@celery.task(name='agent.update')
def update(vm, data):
    pass


@celery.task(name='agent.add_keys')
def add_keys(vm, keys):
    pass


@celery.task(name='agent.del_keys')
def del_keys(vm, keys):
    pass


@celery.task(name='agent.get_keys')
def get_keys(vm):
    pass


@celery.task(name='agent.send_expiration')
def send_expiration(vm, url):
    pass


@celery.task(name='agent.change_ip')
def change_ip(vm, interfaces, dns):
    pass
