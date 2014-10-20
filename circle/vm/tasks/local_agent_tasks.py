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

from django.utils.translation import ugettext_noop

from manager.mancelery import celery


@celery.task
def agent_started(vm, version=None, system=None):
    from vm.models import Instance
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    instance.agent_started(
        user=instance.owner, old_version=version, agent_system=system)


@celery.task
def agent_stopped(vm):
    from vm.models import Instance, InstanceActivity
    instance = Instance.objects.get(id=int(vm.split('-')[-1]))
    qs = InstanceActivity.objects.filter(
        instance=instance, activity_code='vm.Instance.agent')
    act = qs.latest('id')
    with act.sub_activity('stopping', concurrency_check=False,
                          readable_name=ugettext_noop('stopping')):
        pass
