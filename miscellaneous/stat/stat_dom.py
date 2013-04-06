#!/usr/bin/python

import xmltodict
import xml.dom.minidom as minidom
import sys
import json
import math

xml = sys.stdin.read()
data = minidom.parseString(xml)
node = data.documentElement
hosts = data.getElementsByTagName("HOST")

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

for host in hosts:
    share = host.getElementsByTagName("HOST_SHARE")[0]
    cpu_max += int(share.getElementsByTagName("MAX_CPU")[0].childNodes[0].data)
    used_cpu += int(share.getElementsByTagName("USED_CPU")[0].childNodes[0].data)
    cpu_usage += int(share.getElementsByTagName("CPU_USAGE")[0].childNodes[0].data)
    mem_usage += int(share.getElementsByTagName("MEM_USAGE")[0].childNodes[0].data)
    used_mem += int(share.getElementsByTagName("USED_MEM")[0].childNodes[0].data)
    mem_max += int(share.getElementsByTagName("MAX_MEM")[0].childNodes[0].data)
    running_vms += int(share.getElementsByTagName("RUNNING_VMS")[0].childNodes[0].data)

if cpu_usage < used_cpu:
    alloc_cpu = 0
    free_cpu = (cpu_max - used_cpu)
else:
    alloc_cpu = (cpu_usage - used_cpu)
    free_cpu = (cpu_max - alloc_cpu - used_cpu)
#Round memory values
mem_usage = mem_usage / 1024
used_mem = used_mem / 1024
mem_max = mem_max / 1024
if mem_max < (1024*5):
    dimension = "MB"
else:
    mem_usage = mem_usage / 1024
    used_mem = used_mem / 1024
    mem_max = mem_max / 1024
    dimension = "GB"
mem_usage = round(mem_usage, 2)
used_mem = round(used_mem, 2)
mem_max = round(mem_max, 2)

if mem_usage < used_mem:
    alloc_mem = 0
    free_mem = (mem_max - used_mem)
else:
    alloc_mem = (mem_usage - used_mem)
    free_mem = (mem_max - alloc_mem - used_mem)
used_mem = used_mem

cpu_dict = {'FREE_CPU' : free_cpu, 'ALLOC_CPU' : alloc_cpu , 'USED_CPU'  : 
        used_cpu}
mem_dict = {'FREE_MEM' : free_mem, 'ALLOC_MEM' : alloc_mem , 'USED_MEM' :
        used_mem}

print json.dumps({ 'CPU' : cpu_dict, 'MEM' : mem_dict, 'VMS' : running_vms,
    'DIMENSION' : dimension})
