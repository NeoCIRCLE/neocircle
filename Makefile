SHELL := /bin/bash


default: migrate collectstatic mo less uglifyjs restart

pulldef: pull default
pull:
	git pull

po:
	for i in */; do cd $$i; ../manage.py makemessages --all || true; cd ..; done
	for i in */; do cd $$i; ../manage.py makemessages --all -d djangojs || true; cd ..; done

migrate:
	./manage.py migrate

collectstatic:
	./manage.py collectstatic --noinput

mo:
	for i in */locale/*/*/*.po;    do echo -ne "$$i:\t"; msgfmt --statistics $$i;done
	for i in */; do cd $$i; ls locale &>/dev/null && ../manage.py compilemessages || true; cd ..; done

restart:
	sudo /etc/init.d/apache2 reload || sudo restart django

less:
	lessc one/static/style/style.less > one/static/style/style.css

uglifyjs:
	uglifyjs one/static/script/cloud.js > one/static/script/cloud.min.js
	uglifyjs one/static/script/util.js > one/static/script/util.min.js
	uglifyjs one/static/script/store.js > one/static/script/store.min.js
