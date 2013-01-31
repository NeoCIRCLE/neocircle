#!/bin/bash

cd /opt/webadmin/cloud
./manage.py syncdb --noinput
./manage.py migrate
./manage.py loaddata miscellaneous/dump.json
./manage.py loaddata miscellaneous/dev.json
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

for i in cloudstore toplist django
do
    sudo stop $i || true
    sudo cp /opt/webadmin/cloud/miscellaneous/devenv/$i.conf /etc/init/
    sudo start $i
done

cd /opt/webadmin/cloud/miscellaneous/devenv

sudo cp vimrc.local /etc/vim/vimrc.local
exit 0
