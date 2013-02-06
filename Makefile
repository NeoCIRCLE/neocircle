SHELL := /bin/bash


all: migrate collectstatic mo restart

migrate:
	./manage.py migrate

collectstatic:
	./manage.py collectstatic --noinput

mo:
	for i in */; do cd $$i; ../manage.py compilemessages || true; cd ..; done

restart:
	sudo /etc/init.d/apache2 reload
