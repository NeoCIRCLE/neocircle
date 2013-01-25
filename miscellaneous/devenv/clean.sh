#!/bin/bash


if [ "$1" != -f ]
then
    echo 'Clear ALL PRIVATE DATA ON THE VM. This is used for praparing VM template.'
    echo -- '-f switch is required.'
    exit 1
fi


rm -rf /opt/webadmin/cloud*
rm .bash_history
rm -f ~/.gitconfig
mysql <<A
DROP USER webadmin@localhost;
A
mysql <<A
DROP DATABASE webadmin;
A

sudo chpasswd <<<'cloud:ezmiez'
