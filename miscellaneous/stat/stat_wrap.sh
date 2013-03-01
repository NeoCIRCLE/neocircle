#!/bin/bash

export HOME='/var/www'
export LANG='en_US.UTF-8'
export LANGUAGE='en_US:en'
export LOGNAME='www-data'
export MAIL='/var/mail/www-data'
export PATH='/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games'
export PWD='/var/www'
export SHELL='/bin/sh'
export TERM='screen'
export USER='www-data'

#export ONE_LOCATION='/var/lib/opennebula'
export PATH="$PATH:$ONE_LOCATION/bin"

sudo -u oneadmin -i onehost list -x 
