Install
=========

[ ! -e "$SSH_AUTH_SOCK" ] && echo "Please forward the SSH agent." && exit 1
# rabbitmq does not work with hostnames beginning w numbers
hostname=$(hostname)
case "$hostname" in
    [0-9]*)
    sudo tee /etc/hostname <<< c$hostname
    sudo hostname c$hostname
    sudo sed -i /etc/hosts -e "s/$hostname/c$hostname/g"
esac
sudo apt-get update
sudo apt-get install --yes virtualenvwrapper postgresql git \
    python-pip rabbitmq-server libpq-dev python-dev
sudo sed -i /etc/postgresql/9.1/main/postgresql.conf -e '/#listen_addresses/ s/^#//'
sudo /etc/init.d/postgresql restart
sudo sed -i /etc/ssh/sshd_config -e '$ a AcceptEnv GIT_*'
sudo /etc/init.d/ssh reload
sudo -u postgres createuser -S -D -R circle
sudo -u postgres psql <<<"ALTER USER circle WITH PASSWORD 'circle';"
sudo -u postgres createdb circle -O circle
source /etc/bash_completion.d/virtualenvwrapper
git clone -b ng git@git.cloud.ik.bme.hu:circle/cloud.git circle
mkvirtualenv circle
cat >>/home/cloud/.virtualenvs/circle/bin/postactivate <<A
export DJANGO_SETTINGS_MODULE=circle.settings.local
export DJANGO_DB_HOST=localhost
export DJANGO_DB_PASSWORD=circle
export DJANGO_FIREWALL_SETTINGS='{"dns_ip": "152.66.243.60", "dns_hostname":
            "localhost", "dns_ttl": "300", "reload_sleep": "10",
            "rdns_ip": "152.66.243.60", "default_vlangroup": "publikus"}'
A
workon circle
cd ~/circle
pip install -r requirements/local.txt
circle/manage.py syncdb --migrate --noinput
circle/manage.py createsuperuser --username=test --email=test@example.org 

