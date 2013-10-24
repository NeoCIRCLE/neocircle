from calvin import *
import datetime

query = Query()
query.setTarget("2008.vm.ik.bme.hu.circle")
query.setMetric("cpu.usage")
query.setAbsoluteStart("2013", "10", "23", "00", "00")
query.generate()

handler  = GraphiteHandler("10.9.1.209")

times = int(input("How many requests do you intend to send? [postive integer]  "))

global_start = datetime.datetime.now()
for i in range (1,times):
    local_start = datetime.datetime.now()
    handler.put(query)
    handler.send()
    local_end = datetime.datetime.now()
    print((local_end-local_start).microseconds)
global_end = datetime.datetime.now()

print("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
print("Summary:")
print(global_end - global_start)
print("AVG:")
print((global_end -global_start) / times)
print("*-*-*-*-*-*-*-*-*-*-*-*-*-*-*")
