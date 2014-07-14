Installation of a development machine
=====================================

.. highlight:: bash

This tutorial describes the installation of a development environment. To
have a fully working environment, you have to set up the other components
as well. The full procedure is included in the :doc:`Puppet recipes
</puppet>` available for CIRCLE Cloud.

Preparation
-----------

To get the project running on a development machine, launch a new Ubuntu
14.04 machine, and log in to it over SSH.


.. info::
    To use *git* over *SSH*, we advise enabling SSH *agent forwarding*.
    On your terminal computer check if *ssh-agent* is running (the command
    should print a process id)::

      $ echo $SSH_AGENT_PID
      1234

    If it is not running, you can configure your dektop environment to
    automatically launch it.

    Add your private key to the agent (if it is not added by your desktop
    environment)::

      ssh-add [~/.ssh/path_to_id_rsa]

    You can read and write all repositories over https, but you will have to
    provide username and password for every push command.

Log in to the new vm. The :kbd:`-A` switch enables agent forwarding::

  ssh -A cloud@host

You can check agent forwarding on the vm::

  $ if [ -S "$SSH_AUTH_SOCK" ]; then echo "Agent forwarding works!"; fi
  Agent forwarding works!

.. warning::
  If the first character of the hostname of the vm is a digit, you have to
  change it, because RabbitMQ won't work with it. ::

    old=$(hostname)
    new=c-${old}
    sudo tee /etc/hostname <<<$new
    sudo hostname $new
    sudo sed -i /etc/hosts -e "s/$old/$new/g"

Setting up required software
----------------------------

Update the package lists, and install the required system software::

  sudo apt-get update
  sudo apt-get install --yes virtualenvwrapper postgresql git \
    python-pip rabbitmq-server libpq-dev python-dev ntp memcached \
    libmemcached-dev

Set up *PostgreSQL* to listen on localhost and restart it::

  sudo sed -i /etc/postgresql/9.1/main/postgresql.conf -e '/#listen_addresses/ s/^#//'
  sudo /etc/init.d/postgresql restart

Also, create a new database and user::

  sudo -u postgres createuser -S -D -R circle
  sudo -u postgres psql <<<"ALTER USER circle WITH PASSWORD 'circle';"
  sudo -u postgres createdb circle -O circle

Configure RabbitMQ: remove the guest user, add virtual host and user with
proper permissions::

  sudo rabbitmqctl delete_user guest
  sudo rabbitmqctl add_vhost circle
  sudo rabbitmqctl add_user cloud password
  sudo rabbitmqctl set_permissions -p circle cloud '.*' '.*' '.*'

Enable SSH server to accept your name and address from your environment::

  sudo sed -i /etc/ssh/sshd_config -e '$ a AcceptEnv GIT_*'
  sudo /etc/init.d/ssh reload

You should set these vars in your **local** profile::

  cat >>~/.profile <<'END'
  export GIT_AUTHOR_NAME="Your Name"
  export GIT_AUTHOR_EMAIL="your.address@example.org"
  export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
  export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
  END
  source ~/.profile

Allow sending it in your **local** ssh configuration::

  # Content of ~/.ssh/config:
  Host *
    SendEnv GIT_*


Setting up Circle itself
------------------------

Clone the git repository::

  git clone https://git.ik.bme.hu/circle/cloud.git circle

If you want to push back any modifications, it is possible to set SSH as the
push protocol::

  cd circle
  git remote set-url --push origin git@git.ik.bme.hu:circle/cloud.git

Set up *virtualenvwrapper* and the *virtual Python environment* for the
project::

  source /etc/bash_completion.d/virtualenvwrapper
  mkvirtualenv circle

Set up default Circle configuration and activate the virtual environment::

  cat >>/home/cloud/.virtualenvs/circle/bin/postactivate <<END
  export DJANGO_SETTINGS_MODULE=circle.settings.local
  export DJANGO_DB_HOST=localhost
  export DJANGO_DB_PASSWORD=circle
  export DJANGO_FIREWALL_SETTINGS='{"dns_ip": "152.66.243.60", "dns_hostname":
              "localhost", "dns_ttl": "300", "reload_sleep": "10",
              "rdns_ip": "152.66.243.60", "default_vlangroup": "publikus"}'
  export AMQP_URI='amqp://cloud:password@localhost:5672/circle'
  export CACHE_URI='pylibmc://127.0.0.1:11211/'
  END
  workon circle
  cd ~/circle

Install the required Python libraries to the virtual environment::

  pip install -r requirements/local.txt

Sync the database and create a superuser::

  circle/manage.py syncdb --all --noinput
  circle/manage.py migrate --fake
  circle/manage.py createsuperuser --username=test --email=test@example.org

You can now start the development server::

  circle/manage.py runserver '[::]:8080'

You will also need to run a local Celery worker::

  circle/manage.py celery worker -A manager.mancelery

.. note::
  You might run the Celery worker (and also the development server) in GNU
  Screen, or use Upstart::
    sudo cp miscellaneous/mancelery.conf /etc/init/
    sudo start mancelery

Building documentation
----------------------

To build the *docs*, install *make*, go to the docs folder, and run the building
process. ::

  sudo apt-get install make
  cd ~/circle/docs/
  make html

You might also want to serve the generated docs with Python's development
server::

  (cd _build/html && python -m SimpleHTTPServer 8080)

Configuring vim
---------------

To follow the coding style of the project more easily, you might want to
configure vim like we do::

  mkdir -p ~/.vim/autoload ~/.vim/bundle
  curl -Sso ~/.vim/autoload/pathogen.vim \
      https://raw.github.com/tpope/vim-pathogen/master/autoload/pathogen.vim
  cd ~/.vim; mkdir -p bundle; cd bundle && git clone \
      git://github.com/klen/python-mode.git
  cat >>~/.vimrc <<END
      filetype off
      call pathogen#infect()
      call pathogen#helptags()
      filetype plugin indent on
      syntax on
  END
  sudo pip install pyflakes rope pep8 mccabe
