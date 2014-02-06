from hashlib import sha224
from logging import getLogger
from time import time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import (CharField, DateTimeField, ForeignKey,
                              NullBooleanField, TextField)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel

logger = getLogger(__name__)


def activitycontextimpl(act, on_abort=None, on_commit=None):
    try:
        yield act
    except Exception as e:
        handler = None if on_abort is None else lambda a: on_abort(a, e)
        act.finish(succeeded=False, result=str(e), event_handler=handler)
        raise e
    else:
        act.finish(succeeded=True, event_handler=on_commit)


class ActivityModel(TimeStampedModel):
    activity_code = CharField(max_length=100, verbose_name=_('activity code'))
    parent = ForeignKey('self', blank=True, null=True, related_name='children')
    task_uuid = CharField(blank=True, max_length=50, null=True, unique=True,
                          help_text=_('Celery task unique identifier.'),
                          verbose_name=_('task_uuid'))
    user = ForeignKey(User, blank=True, null=True, verbose_name=_('user'),
                      help_text=_('The person who started this activity.'))
    started = DateTimeField(verbose_name=_('started at'),
                            blank=True, null=True,
                            help_text=_('Time of activity initiation.'))
    finished = DateTimeField(verbose_name=_('finished at'),
                             blank=True, null=True,
                             help_text=_('Time of activity finalization.'))
    succeeded = NullBooleanField(blank=True, null=True,
                                 help_text=_('True, if the activity has '
                                             'finished successfully.'))
    result = TextField(verbose_name=_('result'), blank=True, null=True,
                       help_text=_('Human readable result of activity.'))

    def __unicode__(self):
        if self.parent:
            return self.parent.activity_code + "->" + self.activity_code
        else:
            return self.activity_code

    class Meta:
        abstract = True

    def finish(self, succeeded, result=None, event_handler=None):
        if not self.finished:
            self.finished = timezone.now()
            self.succeeded = succeeded
            self.result = result
            if event_handler is not None:
                event_handler(self)
            self.save()

    @property
    def has_succeeded(self):
        return self.finished and self.succeeded

    @property
    def has_failed(self):
        return self.finished and not self.succeeded


def method_cache(memcached_seconds=60, instance_seconds=5):  # noqa
    """Cache return value of decorated method to memcached and memory.

    :param memcached_seconds: Invalidate memcached results after this time.
    :param instance_seconds: Invalidate results cached to static memory after
    this time.

    If a result is cached on instance, return that first.  If that fails, check
    memcached. If all else fails, run the method and cache on instance and in
    memcached.

    Do not use for methods with side effects.
    Instances are hashed by their id attribute, args by their unicode
    representation.

    ** NOTE: Methods that return None are always "recached".
    Based on https://djangosnippets.org/snippets/2477/
    """

    def inner_cache(method):

        def get_key(instance, *args, **kwargs):
            return sha224(unicode(method.__module__) +
                          unicode(method.__name__) +
                          unicode(instance.id) +
                          unicode(args) +
                          unicode(kwargs)).hexdigest()

        def x(instance, *args, **kwargs):
            invalidate = kwargs.pop('invalidate_cache', False)
            now = time()
            key = get_key(instance, *args, **kwargs)

            result = None
            try:
                vals = getattr(instance, key)
            except AttributeError:
                pass
            else:
                if vals['time'] + instance_seconds > now:
                    # has valid on class cache, return that
                    result = vals['value']

            if result is None:
                result = cache.get(key)

            if invalidate or (result is None):
                # all caches failed, call the actual method
                result = method(instance, *args, **kwargs)
                # save to memcache and class attr
                cache.set(key, result, memcached_seconds)
                setattr(instance, key, {'time': now, 'value': result})
                logger.debug('Value of <%s>.%s(%s)=<%s> saved to cache.',
                             unicode(instance), method.__name__,
                             unicode(args), unicode(result))

            return result
        return x

    return inner_cache
