Install
=========

.. highlight:: bash


To get the project running on a development machine, create a new Ubuntu 12.04
instance, and log in to it over SSH.

(To be able to easily copy and paste the commands given, alias :kbd:`$` to nothing:
:kbd:`alias '$='`.)


To use git over SSH, we advise enabling SSH agent forwarding.
On your personal computer check if ssh-agent is running (the command should
print a process id)::
  
  $ echo $SSH_AGENT_PID
  1234

If it is not running, you should set up your login manager or some other
solution to automatically launch it.

Add your primary key to the agent (if it is not added by your desktop
environment)::

  $ ssh-add [~/.ssh/path_to_id_rsa]

Log in to the new vm. The :kbd:`-A` switch enables agent forwarding::

  $ ssh -A cloud@host

You can check agent forwarding on the vm::

  $ if [ -e "$SSH_AUTH_SOCK" ]; than echo "Agent forwarding works!"; fi
  Agent forwarding works!

If the hostname of the vm starts with a digit, you have to change it, because
RabbitMQ won't work with it. ::

  $ old=$(hostname)
  $ new=c-${old}
  $ sudo tee /etc/hostname <<<$new
  $ sudo hostname $new
  $ sudo sed -i /etc/hosts -e "s/$old/$new/g"

Update the package lists, and install the required system software::

  $ sudo apt-get update
  $ sudo apt-get install --yes virtualenvwrapper postgresql git \
      python-pip rabbitmq-server libpq-dev python-dev

Set up PostgreSQL to listen on localhost and restart::

  $ sudo sed -i /etc/postgresql/9.1/main/postgresql.conf -e '/#listen_addresses/ s/^#//'
  $ sudo /etc/init.d/postgresql restart

Also, create a new database and user::

  $ sudo -u postgres createuser -S -D -R circle
  $ sudo -u postgres psql <<<"ALTER USER circle WITH PASSWORD 'circle';"
  $ sudo -u postgres createdb circle -O circle

Enable SSH server to accept your name and address from your environment::

  $ sudo sed -i /etc/ssh/sshd_config -e '$ a AcceptEnv GIT_*'
  $ sudo /etc/init.d/ssh reload

You should set these vars in your *local* profile::

  $ cat >>~/.profile <<'END'
  export GIT_AUTHOR_NAME="Your Name"
  export GIT_AUTHOR_EMAIL="your.address@example.org"
  export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
  export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
  END
  $ source ~/.profile

Allow sending it in your *local* ssh configuration::

  # ~/.ssh/config
  Host *
    SendEnv GIT_*
  

Clone the git repository::

  $ git clone git@git.cloud.ik.bme.hu:circle/cloud.git circle

Set up virtualenvwrapper and the virtual environment for the project::

  $ source /etc/bash_completion.d/virtualenvwrapper
  $ mkvirtualenv circle

Set up default settings and activate the virtual environment::

  $ cat >>/home/cloud/.virtualenvs/circle/bin/postactivate <<END
  export DJANGO_SETTINGS_MODULE=circle.settings.local
  export DJANGO_DB_HOST=localhost
  export DJANGO_DB_PASSWORD=circle
  export DJANGO_FIREWALL_SETTINGS='{"dns_ip": "152.66.243.60", "dns_hostname":
              "localhost", "dns_ttl": "300", "reload_sleep": "10",
              "rdns_ip": "152.66.243.60", "default_vlangroup": "publikus"}'
  END
  $ workon circle
  $ cd ~/circle

Install the required python libraries to the virtual environment::

  $ pip install -r requirements/local.txt

Sync the database and create a superuser::

  $ circle/manage.py syncdb --migrate --noinput
  $ circle/manage.py createsuperuser --username=test --email=test@example.org 

You can now start the development server::

  $ circle/manage.py runserver '[::]:8080'

To build the docs, install make, go to the docs folder, and run the building
process. You might also want to serve it with Python's development server::

  $ sudo apt-get install make
  $ cd ~/circle/docs/
  $ make html
  $ cd _build/html
  $ python -m SimpleHTTPServer 8080
