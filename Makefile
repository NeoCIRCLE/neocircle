SHELL := /bin/bash

jsfiles += one/static/script/cloud.min.js
jsfiles += one/static/script/util.min.js
jsfiles += one/static/script/store.min.js
cssfiles += one/static/style/style.css

default: migrate generatestatic collectstatic mo setbranch restart

pulldef: pull default
pull:
	git pull

po:
	for i in */; do cd $$i; ../manage.py makemessages --all || true; cd ..; done
	for i in */; do cd $$i; ../manage.py makemessages --all -d djangojs || true; cd ..; done

migrate:
	./manage.py migrate

generatestatic: $(jsfiles) $(cssfiles)

collectstatic:
	./manage.py collectstatic --noinput

setbranch:
	sed -i cloud/local_settings.py -e '/RELEASE=/d' || true
	echo "RELEASE='`git rev-parse --abbrev-ref HEAD`'" >>cloud/local_settings.py

mo:
	for i in */locale/*/*/*.po;    do echo -ne "$$i:\t"; msgfmt --statistics $$i;done
	for i in */; do cd $$i; ls locale &>/dev/null && ../manage.py compilemessages || true; cd ..; done

restart:
	sudo /etc/init.d/apache2 reload || sudo restart django

%.min.js: %.js
	uglifyjs $< > $@

%.css: %.less
	lessc one/static/style/style.less > one/static/style/style.css
