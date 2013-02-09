SHELL := /bin/bash


default: migrate collectstatic mo restart

pull: default
	git pull

po:
	for i in */; do cd $$i; ../manage.py makemessages --all || true; cd ..; done
	for i in */; do cd $$i; ../manage.py makemessages --all -d djangojs || true; cd ..; done

migrate:
	./manage.py migrate

collectstatic:
	./manage.py collectstatic --noinput

mo:
	for i in */; do cd $$i; ../manage.py compilemessages || true; cd ..; done

restart:
	sudo /etc/init.d/apache2 reload
