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
