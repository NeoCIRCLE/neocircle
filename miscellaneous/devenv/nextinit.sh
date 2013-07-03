#!/bin/bash

nev=dev-$(hostname)
sudo sed -i /etc/hosts -e "/127.0.1.1/ s/.*/127.0.1.1 $nev.cloud.ik.bme.hu $nev/"
sudo tee /etc/hostname <<<$nev
sudo hostname $nev
sudo /etc/init.d/rabbitmq-server stop || true
sudo /etc/init.d/rabbitmq-server start

sudo pip install django_extensions
sudo pip install django-nose
sudo pip install django-debug-toolbar
for i in cloudstore toplist django
do
    sudo stop $i || true
done

sudo tee /etc/sudoers.d/djangokeep <<A
Defaults        env_keep += DJANGO_DB_PASSWORD
Defaults        env_keep += DJANGO_SECRET_KEY
Defaults        env_keep += DJANGO_SETTINGS_MODULE
A
sudo chmod 0440 /etc/sudoers.d/djangokeep

sudo apt-get install rabbitmq-server gettext memcached npm nodejs
sudo rabbitmqctl delete_user guest || true
sudo rabbitmqctl add_user nyuszi teszt || true
sudo rabbitmqctl add_vhost django || true
sudo rabbitmqctl set_permissions -p django nyuszi '.*' '.*' '.*' || true

sudo pip install python-memcached
sudo npm install -g less@1.3.3
sudo npm install -g uglify-js@1

sudo cp /opt/webadmin/cloud/miscellaneous/devenv/boot_url.py /opt/

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
    sudo cp /opt/webadmin/cloud/miscellaneous/devenv/$i.conf /etc/init/
    sudo start $i
done

cat <<A >>~/.profile
export DJANGO_SETTINGS_MODULE=cloud.settings.dev
export DJANGO_DB_PASSWORD=asjklddfjklqjf
export DJANGO_SECRET_KEY=asjklddfjklqjfasjklddfjklqjfasjklddfjklqjf
A
. ~/.profile
set -x
cd /opt/webadmin/cloud
./manage.py syncdb --noinput
./manage.py migrate
./manage.py loaddata miscellaneous/dump.json
./manage.py loaddata miscellaneous/devenv/dev.json
./manage.py update
./manage.py loaddata miscellaneous/devenv/dev.json
set +x



cd /opt/webadmin/cloud/miscellaneous/devenv

sudo cp vimrc.local /etc/vim/vimrc.local


cd /opt/webadmin/cloud
./manage.py changepassword test

git config --global alias.prettylog 'log --graph --all --decorate --date-order --pretty="%C(yellow)%h%Cred%d%Creset - %C(cyan)%an %Creset: %s %Cgreen(%ar)"'
git config --global alias.civ 'commit --interactive --verbose'
git config --global color.ui true
git config --global core.editor vim

echo Python-mode? [N/y]
read 
if [ "$REPLY" = y ]
then
    mkdir -p ~/.vim/autoload ~/.vim/bundle
    curl -Sso ~/.vim/autoload/pathogen.vim \
        https://raw.github.com/tpope/vim-pathogen/master/autoload/pathogen.vim
    cd ~/.vim; mkdir -p bundle; cd bundle && git clone \
        git://github.com/klen/python-mode.git
    cat >>~/.vimrc <<A
    " Pathogen load
    filetype off

    call pathogen#infect()
    call pathogen#helptags()

    filetype plugin indent on
    syntax on
A
    sudo pip install pyflakes rope pep8 mccabe     
fi


true


