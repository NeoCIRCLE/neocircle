SHELL := /bin/bash

jsfiles += one/static/script/cloud.min.js
jsfiles += one/static/script/util.min.js
jsfiles += one/static/script/store.min.js

default: migrate generatestatic collectstatic mo restart

pulldef: pull default
pull:
	git pull

po:
	for i in */; do cd $$i; ../manage.py makemessages --all || true; cd ..; done
	for i in */; do cd $$i; ../manage.py makemessages --all -d djangojs || true; cd ..; done
	msgmerge firewall/locale/hu/LC_MESSAGES/django.po network/locale/hu/LC_MESSAGES/djangojs.po -o tmp.po
	mv tmp.po network/locale/hu/LC_MESSAGES/djangojs.po

migrate:
	./manage.py syncdb || true
	./manage.py migrate

generatestatic: $(jsfiles) one/static/style/style.css

collectstatic:
	./manage.py collectstatic --noinput

mo:
	for i in */locale/*/*/*.po;    do echo -ne "$$i:\t"; msgfmt --statistics $$i;done
	for i in */; do cd $$i; ls locale &>/dev/null && ../manage.py compilemessages || true; cd ..; done

restart:
	sudo /etc/init.d/apache2 reload || sudo restart django

%.min.js: %.js
	uglifyjs $< > $@

one/static/style/style.css:
	lessc one/static/style/style.less > one/static/style/style.css

.PHONY: default pulldef pull po migrate generatestatic collectstatic mo restart one/static/style/style.css
