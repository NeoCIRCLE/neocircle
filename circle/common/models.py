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
from functools import update_wrapper
from hashlib import sha224
from itertools import chain, imap
from logging import getLogger
from time import time
from warnings import warn

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import (
    CharField, DateTimeField, ForeignKey, NullBooleanField
)
from django.template import defaultfilters
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.translation import ugettext_lazy as _, ugettext_noop
from jsonfield import JSONField

from manager.mancelery import celery
from model_utils.models import TimeStampedModel

logger = getLogger(__name__)


class WorkerNotFound(Exception):
    pass


def get_error_msg(exception):
    try:
        return unicode(exception)
    except UnicodeDecodeError:
        return unicode(str(exception), encoding='utf-8', errors='replace')


def activitycontextimpl(act, on_abort=None, on_commit=None):
    result = None
    try:
        try:
            yield act
        except HumanReadableException as e:
            result = e
            raise
        except BaseException as e:
            # BaseException is the common parent of Exception and
            # system-exiting exceptions, e.g. KeyboardInterrupt
            result = create_readable(
                ugettext_noop("Failure."),
                ugettext_noop("Unhandled exception: %(e)s: %(error)s"),
                e=str(e.__class__.__name__),
                error=get_error_msg(e))
            raise
    except:
        logger.exception("Failed activity %s" % unicode(act))
        handler = None if on_abort is None else lambda a: on_abort(a, e)
        act.finish(succeeded=False, result=result, event_handler=handler)
        raise
    else:
        act.finish(succeeded=True, event_handler=on_commit)


activity_context = contextmanager(activitycontextimpl)


activity_code_separator = '.'


def has_prefix(activity_code, *prefixes):
    """Determine whether the activity code has the specified prefix.

    >>> assert has_prefix('foo.bar.buz', 'foo.bar')
    >>> assert has_prefix('foo.bar.buz', 'foo', 'bar')
    >>> assert has_prefix('foo.bar.buz', 'foo.bar', 'buz')
    >>> assert has_prefix('foo.bar.buz', 'foo', 'bar', 'buz')
    >>> assert not has_prefix('foo.bar.buz', 'foo', 'buz')
    """
    def equal(a, b): return a == b
    act_code_parts = split_activity_code(activity_code)
    prefixes = chain(*imap(split_activity_code, prefixes))
    return all(imap(equal, act_code_parts, prefixes))


def has_suffix(activity_code, *suffixes):
    """Determine whether the activity code has the specified suffix.

    >>> assert has_suffix('foo.bar.buz', 'bar.buz')
    >>> assert has_suffix('foo.bar.buz', 'bar', 'buz')
    >>> assert has_suffix('foo.bar.buz', 'foo.bar', 'buz')
    >>> assert has_suffix('foo.bar.buz', 'foo', 'bar', 'buz')
    >>> assert not has_suffix('foo.bar.buz', 'foo', 'buz')
    """
    def equal(a, b): return a == b
    act_code_parts = split_activity_code(activity_code)
    suffixes = list(chain(*imap(split_activity_code, suffixes)))
    return all(imap(equal, reversed(act_code_parts), reversed(suffixes)))


def join_activity_code(*args):
    """Join the specified parts into an activity code.

    :returns: Activity code string.
    """
    return activity_code_separator.join(args)


def split_activity_code(activity_code):
    """Split the specified activity code into its parts.

    :returns: A list of activity code parts.
    """
    return activity_code.split(activity_code_separator)


class Encoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            obj = force_text(obj)
        try:
            return super(Encoder, self).default(obj)
        except TypeError:
            return unicode(obj)


class ActivityModel(TimeStampedModel):
    activity_code = CharField(max_length=100, verbose_name=_('activity code'))
    readable_name_data = JSONField(blank=True, null=True,
                                   dump_kwargs={"cls": Encoder},
                                   verbose_name=_('human readable name'),
                                   help_text=_('Human readable name of '
                                               'activity.'))
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
    result_data = JSONField(verbose_name=_('result'), blank=True, null=True,
                            dump_kwargs={"cls": Encoder},
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

    @property
    def readable_name(self):
        return HumanReadableObject.from_dict(self.readable_name_data)

    @readable_name.setter
    def readable_name(self, value):
        self.readable_name_data = None if value is None else value.to_dict()

    @property
    def result(self):
        return HumanReadableObject.from_dict(self.result_data)

    @result.setter
    def result(self, value):
        if isinstance(value, basestring):
            warn("Using string as result value is deprecated. Use "
                 "HumanReadableObject instead.",
                 DeprecationWarning, stacklevel=2)
            value = create_readable(user_text_template="",
                                    admin_text_template=value)
        elif not hasattr(value, "to_dict"):
            warn("Use HumanReadableObject.", DeprecationWarning, stacklevel=2)
            value = create_readable(user_text_template="",
                                    admin_text_template=unicode(value))

        self.result_data = None if value is None else value.to_dict()

    @classmethod
    def construct_activity_code(cls, code_suffix, sub_suffix=None):
        code = join_activity_code(cls.ACTIVITY_CODE_BASE, code_suffix)
        if sub_suffix:
            return join_activity_code(code, sub_suffix)
        else:
            return code


@celery.task()
def compute_cached(method, instance, memcached_seconds,
                   key, start, *args, **kwargs):
    """Compute and store actual value of cached method."""
    if isinstance(method, basestring):
        model, id = instance
        instance = model.objects.get(id=id)
        try:
            method = getattr(model, method)
            while hasattr(method, '_original') or hasattr(method, 'fget'):
                try:
                    method = method._original
                except AttributeError:
                    method = method.fget
        except AttributeError:
            logger.exception("Couldnt get original method of %s",
                             unicode(method))
            raise

    #  call the actual method
    result = method(instance, *args, **kwargs)
    # save to memcache
    cache.set(key, result, memcached_seconds)
    elapsed = time() - start
    cache.set("%s.cached" % key, 2, max(memcached_seconds * 0.5,
                                        memcached_seconds * 0.75 - elapsed))
    logger.debug('Value of <%s>.%s(%s)=<%s> saved to cache (%s elapsed).',
                 unicode(instance), method.__name__, unicode(args),
                 unicode(result), elapsed)
    return result


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

        method_name = method.__name__

        def get_key(instance, *args, **kwargs):
            return sha224(unicode(method.__module__) +
                          method_name +
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
                    setattr(instance, key, {'time': now, 'value': result})

            if result is None:
                result = cache.get(key)

            if invalidate or (result is None):
                logger.debug("all caches failed, compute now")
                result = compute_cached(method, instance, memcached_seconds,
                                        key, time(), *args, **kwargs)
                setattr(instance, key, {'time': now, 'value': result})
            elif not cache.get("%s.cached" % key):
                logger.debug("caches expiring, compute async")
                cache.set("%s.cached" % key, 1, memcached_seconds * 0.5)
                try:
                    compute_cached.apply_async(
                        queue='localhost.man', kwargs=kwargs, args=[
                            method_name, (instance.__class__, instance.id),
                            memcached_seconds, key, time()] + list(args))
                except:
                    logger.exception("Couldnt compute async %s", method_name)

            return result

        update_wrapper(x, method)
        x._original = method
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

    def deconstruct(self):
        name, path, args, kwargs = super(HumanSortField, self).deconstruct()
        if self.monitor is not None:
            kwargs['monitor'] = self.monitor
        return name, path, args, kwargs

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


class HumanReadableObject(object):
    def __init__(self, user_text_template, admin_text_template, params):
        self._set_values(user_text_template, admin_text_template, params)

    def _set_values(self, user_text_template, admin_text_template, params):
        if isinstance(user_text_template, Promise):
            user_text_template = user_text_template._proxy____args[0]
        if isinstance(admin_text_template, Promise):
            admin_text_template = admin_text_template._proxy____args[0]
        self.user_text_template = user_text_template
        self.admin_text_template = admin_text_template
        for k, v in params.iteritems():
            try:
                v = timezone.datetime.strptime(
                    v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.UTC())
            except (ValueError, TypeError):  # Mock raises TypeError
                pass
            if isinstance(v, timezone.datetime):
                params[k] = defaultfilters.date(v, "DATETIME_FORMAT")
        self.params = params

    @classmethod
    def create(cls, user_text_template, admin_text_template=None, **params):
        return cls(user_text_template=user_text_template,
                   admin_text_template=(admin_text_template or
                                        user_text_template), params=params)

    def set(self, user_text_template, admin_text_template=None, **params):
        self._set_values(user_text_template,
                         admin_text_template or user_text_template, params)

    @classmethod
    def from_dict(cls, d):
        return None if d is None else cls(**d)

    def _get_parsed_text(self, key):
        value = getattr(self, key)
        if value == "":
            return ""
        try:
            return _(value) % self.params
        except KeyError:
            logger.exception("Can't render %s '%s' %% %s",
                             key, value, unicode(self.params))
            raise

    def get_admin_text(self):
        try:
            return self._get_parsed_text("admin_text_template")
        except KeyError:
            return self.get_user_text()

    def get_user_text(self):
        try:
            return self._get_parsed_text("user_text_template")
        except KeyError:
            return self.user_text_template

    def get_text(self, user):
        if user and user.is_superuser:
            return self.get_admin_text()
        else:
            return self.get_user_text()

    def to_dict(self):
        return {"user_text_template": self.user_text_template,
                "admin_text_template": self.admin_text_template,
                "params": self.params}

    def __unicode__(self):
        return self.get_user_text()


create_readable = HumanReadableObject.create


class HumanReadableException(HumanReadableObject, Exception):
    """HumanReadableObject that is an Exception so can used in except clause.
    """

    def __init__(self, level=None, *args, **kwargs):
        super(HumanReadableException, self).__init__(*args, **kwargs)
        if level is not None:
            if hasattr(messages, level):
                self.level = level
            else:
                raise ValueError(
                    "Level should be the name of an attribute of django."
                    "contrib.messages (and it should be callable with "
                    "(request, message)). Like 'error', 'warning'.")
        elif not hasattr(self, "level"):
            self.level = "error"

    def send_message(self, request, level=None):
        msg = self.get_text(request.user)
        getattr(messages, level or self.level)(request, msg)


def fetch_human_exception(exception, user=None):
    """Fetch user readable message from exception.

    >>> r = humanize_exception("foo", Exception())
    >>> fetch_human_exception(r, User())
    u'foo'
    >>> fetch_human_exception(r).get_text(User())
    u'foo'
    >>> fetch_human_exception(Exception(), User())
    u'Unknown error'
    >>> fetch_human_exception(PermissionDenied(), User())
    u'Permission Denied'
    """

    if not isinstance(exception, HumanReadableException):
        if isinstance(exception, PermissionDenied):
            exception = create_readable(ugettext_noop("Permission Denied"))
        else:
            exception = create_readable(ugettext_noop("Unknown error"),
                                        ugettext_noop("Unknown error: %(ex)s"),
                                        ex=unicode(exception))
    return exception.get_text(user) if user else exception


def humanize_exception(message, exception=None, level=None, **params):
    """Return new dynamic-class exception which is based on
    HumanReadableException and the original class with the dict of exception.

    >>> try: raise humanize_exception("Welcome!", TypeError("hello"))
    ... except HumanReadableException as e: print e.get_admin_text()
    ...
    Welcome!
    """

    Ex = type("HumanReadable" + type(exception).__name__,
              (HumanReadableException, type(exception)),
              exception.__dict__)
    ex = Ex.create(message, **params)
    if level:
        ex.level = level
    return ex
