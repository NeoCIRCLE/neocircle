from django.conf.urls import patterns, url

from ..views import vm_ops


urlpatterns = patterns('',
                       *(url(r'^%s/$' % op, v.as_view(), name=v.get_urlname())
                         for op, v in vm_ops.iteritems()))
