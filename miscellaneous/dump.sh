#!/bin/bash


/opt/webadmin/cloud/manage.py dumpdata --format=json --indent=2|grep -v '"password":'|sed -e 's/^.*"smb_password":.*$/"smb_password": "kamu",/' -e 's/BEGIN RSA PRIVATE.*END RSA/xxx/' >/opt/webadmin/cloud/miscellaneous/dump.json

