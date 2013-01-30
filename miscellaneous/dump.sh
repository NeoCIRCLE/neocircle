#!/bin/bash


/opt/webadmin/cloud/manage.py dumpdata -e admin -e one.userclouddetails -e school -e auth.permission -e contenttypes -e sessions -e djcelery --format=json --indent=2|grep -v '"password":'|sed -e 's/^.*"smb_password":.*$/"smb_password": "kamu",/' -e 's/BEGIN RSA PRIVATE.*END RSA/xxx/' >/opt/webadmin/cloud/miscellaneous/dump.json


