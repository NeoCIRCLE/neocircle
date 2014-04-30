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

from calvin import *  # noqa
import datetime

query = Query()
query.setTarget("2008.vm.ik.bme.hu.circle")
query.setMetric("cpu.usage")
query.setAbsoluteStart("2013", "10", "23", "00", "00")
query.generate()

handler = GraphiteHandler("10.9.1.209")

times = int(input(
    "How many requests do you intend to send? [postive integer]  "))

global_start = datetime.datetime.now()
for i in range(1, times):
    local_start = datetime.datetime.now()
    handler.put(query)
    handler.send()
    local_end = datetime.datetime.now()
    print((local_end - local_start).microseconds)
global_end = datetime.datetime.now()

print("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
print("Summary:")
print(global_end - global_start)
print("AVG:")
print((global_end - global_start) / times)
print("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
