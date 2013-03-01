#!/usr/bin/python

import xmltodict
import sys
import json


xml = sys.stdin.read()
data = xmltodict.parse(xml)


#CPU stat
cpu_usage = 0
used_cpu = 0
cpu_max = 0
#Memory stat
mem_usage = 0
used_mem = 0
mem_max = 0
#Running VMs
running_vms = 0
print "\n" .join(data["HOST_POOL"]["HOST"])
for host in data["HOST_POOL"]:
    cpu_max += int(host["HOST_SHARE"]["MAX_CPU"])
    used_cpu += int(host["HOST_SHARE"]["USED_CPU"])
    cpu_usage += int(host["HOST_SHARE"]["CPU_USAGE"])
    mem_usage += int(host["HOST_SHARE"]["MEM_USAGE"])
    used_mem += int(host["HOST_SHARE"]["USED_MEM"])
    mem_max += int(host["HOST_SHARE"]["MAX_MEM"])
    running_vms += int(host["HOST_SHARE"]["RUNNING_VMS"])

free_cpu = cpu_max - cpu_usage - used_cpu
alloc_cpu = cpu_usage - used_cpu
free_mem = mem_max - mem_usage - used_mem
alloc_mem = mem_usage - used_mem
cpu_dict = {'FREE_CPU' : free_cpu, 'ALLOC_CPU' : alloc_cpu , 'USED_CPU'  : 
        used_cpu}
mem_dict = {'FREE_MEM' : free_mem, 'ALLOC_MEM' : alloc_mem , 'USED_MEM' :
        used_mem}

print json.dumps(cpu_dict)
print json.dumps(mem_dict)
print "Running VMs: " + str(running_vms)
print "Global MAX CPU: " + str(cpu_max)
print "Allocated CPU: " + str(cpu_usage)
print "CPU under load: " + str(used_cpu)
print "CPU diff alloc-load: " + str(cpu_usage-used_cpu)
