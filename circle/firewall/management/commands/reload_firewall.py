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

from __future__ import unicode_literals, absolute_import

from django.core.management.base import BaseCommand

from firewall.tasks.local_tasks import reloadtask

from argparse import ArgumentTypeError


class Command(BaseCommand):

    def add_arguments(self, parser):

        parser.add_argument('--sync',
                            action='store_const',
                            dest='sync',
                            const=True,
                            default=False,
                            help='synchronous reload')

        parser.add_argument('--timeout',
                            action='store',
                            dest='timeout',
                            default=15,
                            type=self.positive_int,
                            help='timeout for synchronous reload')

    def handle(self, *args, **options):

        reloadtask('Vlan', sync=options["sync"], timeout=options["timeout"])

    def positive_int(self, val):

        if not val.isdigit():
            raise ArgumentTypeError("'%s' is not a valid positive int" % val)

        return int(val)
