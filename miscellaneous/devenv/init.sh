#!/bin/bash

if [ -z "$SSH_AUTH_SOCK" ]
then
        cat <<A
        Use SSH authentication agent forwarding ("ssh -A cloud@host").
        On the client side you can use "ssh-add [filename]" to let the agent know more keys.
        In .ssh/config you can also use "ForwardAgent yes" setting.
A
        exit 1
fi


if ! git config user.name
then
        echo -n "Your name: "
        read NAME
        git config --global user.name "$NAME"
fi



mysql <<A
DROP USER webadmin@localhost;
A
mysql <<A
DROP DATABASE webadmin;
A

set -e

mysql <<A
CREATE USER webadmin@localhost IDENTIFIED BY 'asjklddfjklqjf';
CREATE DATABASE webadmin CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL ON webadmin.* TO webadmin@localhost;
A


cd /opt/webadmin/
mv cloud cloud.$(date +%s) || true


git clone 'ssh://git@giccero.cloud.ik.bme.hu/cloud'

cd cloud
./manage.py syncdb --noinput
./manage.py migrate
./manage.py createsuperuser --email=cloud@ik.bme.hu
./manage.py loaddata /home/cloud/user.yaml 2>/dev/null || true
./manage.py loaddata /home/cloud/fw.yaml
./manage.py loaddata /home/cloud/one.yaml
./manage.py loaddata /home/cloud/store.yaml
./manage.py update

#Set up store server
rm -rf /var/www/*
mkdir -p /var/www
cd /opt/webadmin/cloud/miscellaneous/store-server/
LOCAL_IP=$(ip addr show dev eth0|grep inet|head -1|awk '{print $2}'|cut -d '/' -f 1)
cat <<EOF > store.config
[store]
#Default root folder (for download and upload)
root_www_folder = /var/www
#Deafult binary folder (for executables)
root_bin_folder = /opt/webadmin/cloud/miscellaneous/store-server/
#Site host (for standalone server)
site_host = 0.0.0.0
#Site port (for standalone server)
site_port = 9000
#Site url (for download and upload links) %(variable)formatter ex: %(port)s
site_url = http://${LOCAL_IP}:%(site_port)s
#User manager script (add, del, set, update)
user_manager = FAKEUserManager.sh
#Temporary directory
temp_dir = /tmp/dl
EOF
sudo /opt/webadmin/cloud/miscellaneous/store-server/CloudStore.py >/dev/null 2>&1 &
