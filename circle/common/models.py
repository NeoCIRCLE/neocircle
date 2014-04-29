# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from collections import deque
from contextlib import contextmanager
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


class WorkerNotFound(Exception):
    pass


def activitycontextimpl(act, on_abort=None, on_commit=None):
    try:
        yield act
    except BaseException as e:
        # BaseException is the common parent of Exception and
        # system-exiting exceptions, e.g. KeyboardInterrupt
        handler = None if on_abort is None else lambda a: on_abort(a, e)
        act.finish(succeeded=False, result=str(e), event_handler=handler)
        raise e
    else:
        act.finish(succeeded=True, event_handler=on_commit)


activity_context = contextmanager(activitycontextimpl)


activity_code_separator = '.'


def join_activity_code(*args):
    """Join the specified parts into an activity code.
    """
    return activity_code_separator.join(args)


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
            if result is not None:
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


class HumanSortField(CharField):
    """
    A CharField that monitors another field on the same model and sets itself
    to a normalized value, which can be used for sensible lexicographycal
    sorting for fields containing numerals. (Avoiding technically correct
    orderings like [a1, a10, a2], which can be annoying for file or host
    names.)

    Apart from CharField's default arguments, an argument is requered:
        - monitor   sets the base field, whose value is normalized.
        - maximum_number_length    can also be provided, and defaults to 4. If
        you have to sort values containing numbers greater than 9999, you
        should increase it.

    Code is based on carljm's django-model-utils.
    """
    def __init__(self, *args, **kwargs):
        logger.debug('Initing HumanSortField(%s %s)',
                     unicode(args), unicode(kwargs))
        kwargs.setdefault('default', "")
        self.maximum_number_length = kwargs.pop('maximum_number_length', 4)
        monitor = kwargs.pop('monitor', None)
        if not monitor:
            raise TypeError(
                '%s requires a "monitor" argument' % self.__class__.__name__)
        self.monitor = monitor
        kwargs['blank'] = True
        super(HumanSortField, self).__init__(*args, **kwargs)

    def get_monitored_value(self, instance):
        return getattr(instance, self.monitor)

    @staticmethod
    def _partition(s, pred):
        """Partition a deque of chars to a tuple of a
           - string of the longest prefix matching pred,
           - string of the longest prefix after the former one not matching,
           - deque of the remaining characters.

           >>> HumanSortField._partition(deque("1234abc567"),
           ...                           lambda s: s.isdigit())
           ('1234', 'abc', deque(['5', '6', '7']))
           >>> HumanSortField._partition(deque("12ab"), lambda s: s.isalpha())
           ('', '12', deque(['a', 'b']))
        """
        match, notmatch = deque(), deque()
        while s and pred(s[0]):
            match.append(s.popleft())
        while s and not pred(s[0]):
            notmatch.append(s.popleft())
        return (''.join(match), ''.join(notmatch), s)

    def get_normalized_value(self, val):
        logger.debug('Normalizing value: %s', val)
        norm = ""
        val = deque(val)
        while val:
            numbers, letters, val = self._partition(val,
                                                    lambda s: s[0].isdigit())
            if numbers:
                norm += numbers.rjust(self.maximum_number_length, '0')
            norm += letters
        logger.debug('Normalized value: %s', norm)
        return norm

    def pre_save(self, model_instance, add):
        logger.debug('Pre-saving %s.%s. %s',
                     model_instance, self.attname, add)
        value = self.get_normalized_value(
            self.get_monitored_value(model_instance))
        setattr(model_instance, self.attname, value[:self.max_length])
        return super(HumanSortField, self).pre_save(model_instance, add)

# allow South to handle these fields smoothly
try:
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules(rules=[
        (
            (HumanSortField,),
            [],
            {'monitor': ('monitor', {}),
             'maximum_number_length': ('maximum_number_length', {}), }
        ),
    ], patterns=['common\.models\.'])
except ImportError:
    pass
