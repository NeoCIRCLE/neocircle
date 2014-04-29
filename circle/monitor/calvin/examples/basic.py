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

server_name = "0.0.0.0"
server_port = "8080"

query = Query()
query.setTarget("1889.foo.fook.fookie.com.DOMAIN")
query.setMetric("cpu.usage")
query.setFormat("json")  # Not neccesary, default is json
query.setRelativeStart(1, "minutes")  # Current cpu usage

query.generate()
# print(query.getGenerated())

print(query.getStart())
# query.setAbsoluteStart("1889", "04", "20", "00", "00")
# query.setRelativeEnd(...)
# query.setAbsoluteEnd(...)

handler = GraphiteHandler(server_name, server_port)

handler.put(query)
handler.send()
response = handler.pop()

print(response["target"])
print(response["datapoints"])
