from django.core.management import setup_environ
from cloud import settings
from school.models import Course

setup_environ(settings)


with open('/home/django/targykodok.csv') as f:
    for l in f.readlines():
        nep, name = l.split("\\")
        o, created = Course.objects.get_or_create(code=nep)
        try:
            o.name = name
            o.save()
        except:
            o.name = "%s (%s)" % (name, nep.replace("BMEVIII", ""))
            o.save()

