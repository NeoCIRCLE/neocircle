#!/usr/bin/python

import base64
import xmltodict
import urllib2
import sys

xml = base64.b64decode(sys.argv[1])
data = xmltodict.parse(xml)
try:
    booturl = data["VM"]["TEMPLATE"]["CONTEXT"]["BOOTURL"]
    (drop, b) = booturl.split(".hu", 1)
    req=urllib2.Request("http://localhost:8080"+b)
    response = urllib2.urlopen(req)
except:
    print 'Error'

