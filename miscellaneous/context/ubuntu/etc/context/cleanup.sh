#!/bin/bash

if [ ! -f /run/context-cleanup ]; then
    exit 0
fi

stop rsyslog
echo -e "auto lo\niface lo inet loopback\n" > /etc/network/interfaces
sed -i 's/^<volume user=.*//' /etc/security/pam_mount.conf.xml
rm -rf ~cloud/{.bash_history,.ssh/id_rsa}
rm -rf ~root/{.bash_history}
rm -rf /etc/ssh/ssh_host_*
rm -rf /usr/NX/home/nx/.ssh/known_hosts
