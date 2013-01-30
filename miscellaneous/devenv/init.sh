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
        echo -n "Your e-mail address: "
        read MAIL
        git config --global user.email "$MAIL"
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
source miscellaneous/devenv/nextinit.sh
