from datetime import datetime

from django import template
from django.utils.timesince import timesince

register = template.Library()


@register.simple_tag(name="bytes_to_megabytes")
def bytes_to_megabytes(size):
    if size:
        return size / (1024 * 1024)
    else:
        return 0


@register.simple_tag(name="timestamp_to_date")
def timestamp_to_date(timestamp):
    date = datetime.fromtimestamp(float(timestamp))
    if (datetime.now() - date).days < 1:
        date = timesince(date)
    return date
