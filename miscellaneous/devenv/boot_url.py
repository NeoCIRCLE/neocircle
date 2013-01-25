#!/usr/bin/python

import base64
import xmltodict
import urllib2
import sys

xml = base64.b64decode(sys.argv[1])
data = xmltodict.parse(xml)
try:
    booturl = data["VM"]["TEMPLATE"]["CONTEXT"]["BOOTURL"]
except:
    print 'Error'
req=urllib2.Request(booturl)
response = urllib2.urlopen(req)

