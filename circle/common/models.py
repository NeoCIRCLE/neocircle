from django.contrib.auth.models import User
from django.db.models import (CharField, DateTimeField, ForeignKey, TextField)
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel


def activitycontextimpl(act):
    try:
        yield act
    except Exception as e:
        act.finish(str(e))
        raise e
    else:
        act.finish()


class ActivityModel(TimeStampedModel):
    activity_code = CharField(max_length=100, verbose_name=_('activity code'))
    parent = ForeignKey('self', blank=True, null=True)
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
    result = TextField(verbose_name=_('result'), blank=True, null=True,
                       help_text=_('Human readable result of activity.'))

    class Meta:
        abstract = True

    def finish(self, result=None):
        if not self.finished:
            self.finished = timezone.now()
            self.result = result
            self.save()
