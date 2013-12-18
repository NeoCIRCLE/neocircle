import logging

from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    ManyToManyField, ForeignKey, CharField, Model, IntegerField, Q
)

logger = logging.getLogger(__name__)


class Level(Model):

    """Definition of a permission level.

    Instances are automatically populated based on AclBase."""
    name = CharField('name', max_length=50)
    content_type = ForeignKey(ContentType)
    codename = CharField('codename', max_length=100)
    weight = IntegerField('weight', null=True)

    def __unicode__(self):
        return "<%s/%s>" % (unicode(self.content_type), self.name)

    class Meta:
        unique_together = (('content_type', 'codename'),
                           # ('content_type', 'weight'),
                           # TODO find a way of temp. disabling this constr.
                           )


class ObjectLevel(Model):

    """Permission level for a specific object."""
    level = ForeignKey(Level)
    content_type = ForeignKey(ContentType)
    object_id = CharField(max_length=255)
    content_object = GenericForeignKey()
    users = ManyToManyField(User)
    groups = ManyToManyField(Group)

    def __unicode__(self):
        return "<%s: %s>" % (unicode(self.content_object), unicode(self.level))

    class Meta:
        unique_together = (('content_type', 'object_id', 'level'),)


class AclBase(Model):

    """Define permission levels for Users/Groups per object."""
    object_level_set = GenericRelation(ObjectLevel)

    @classmethod
    def get_level_object(cls, level):

        """Get Level object for this model by codename."""
        ct = ContentType.objects.get_for_model(cls)
        return Level.objects.get(codename=level, content_type=ct)

    def set_level(self, whom, level):

        """Set level of object for a user or group.

        :param whom: user or group the level is set for
        :type whom: User or Group
        :param level: codename of level to set, or None
        :type level: Level or str or unicode or NoneType
        """
        if isinstance(whom, User):
            self.set_user_level(whom, level)
        elif isinstance(whom, Group):
            self.set_group_level(whom, level)
        else:
            raise AttributeError('"whom" must be a User or Group object.')

    def set_user_level(self, user, level):

        """Set level of object for a user.

        :param whom: user the level is set for
        :type whom: User
        :param level: codename of level to set, or None
        :type level: Level or str or unicode or NoneType
        """
        logger.info('%s.set_user_level(%s, %s) called',
                    *[unicode(p) for p in [self, user, level]])
        if level is None:
            pk = None
        else:
            if isinstance(level, basestring):
                level = self.get_level_object(level)
            if not self.object_level_set.filter(level_id=level.pk).exists():
                self.object_level_set.create(level=level)
            pk = level.pk
        for i in self.object_level_set.all():
            if i.level_id != pk:
                i.users.remove(user)
            else:
                i.users.add(user)
            i.save()

    def set_group_level(self, group, level):

        """Set level of object for a user.

        :param whom: user the level is set for
        :type whom: User or unicode or str
        :param level: codename of level to set
        :type level: str or unicode
        """
        logger.info('%s.set_group_level(%s, %s) called',
                    *[unicode(p) for p in [self, group, level]])
        if level is None:
            pk = None
        else:
            if isinstance(level, basestring):
                level = self.get_level_object(level)
            if not self.object_level_set.filter(level_id=level.pk).exists():
                self.object_level_set.create(level=level)
            pk = level.pk
        for i in self.object_level_set.all():
            if i.level_id != pk:
                i.groups.remove(group)
            else:
                i.groups.add(group)
            i.save()

    def has_level(self, user, level, group_also=True):
        logger.debug('%s.has_level(%s, %s, %s) called',
                     *[unicode(p) for p in [self, user, level, group_also]])
        if user is None or not user.is_authenticated():
            return False
        if getattr(user, 'is_superuser', False):
            logger.debug('- superuser granted')
            return True
        if isinstance(level, basestring):
            level = self.get_level_object(level)
            logger.debug("- level set by str: %s", unicode(level))

        object_levels = self.object_level_set.filter(
            level__weight__gte=level.weight).all()
        groups = user.groups.values_list('id', flat=True) if group_also else []
        for i in object_levels:
            if i.users.filter(pk=user.pk).exists():
                return True
            if group_also and i.groups.filter(pk__in=groups).exists():
                return True
        return False

    def get_users_with_level(self):
        logger.debug('%s.get_users_with_level() called', unicode(self))
        object_levels = (self.object_level_set.select_related(
            'users', 'level').all())
        users = []
        for object_level in object_levels:
            name = object_level.level.codename
            olusers = object_level.users.all()
            users.extend([(u, name) for u in olusers])
            logger.debug('- %s: %s' % (name, [u.username for u in olusers]))
        return users

    def get_groups_with_level(self):
        logger.debug('%s.get_groups_with_level() called', unicode(self))
        object_levels = (self.object_level_set.select_related(
            'groups', 'level').all())
        groups = []
        for object_level in object_levels:
            name = object_level.level.codename
            olgroups = object_level.groups.all()
            groups.extend([(g, name) for g in olgroups])
            logger.debug('- %s: %s' % (name, [g.name for g in olgroups]))
        return groups

    @classmethod
    def get_objects_with_level(cls, level, user):
        logger.debug('%s.get_objects_with_level(%s,%s) called',
                     unicode(cls), unicode(level), unicode(user))
        if user is None or not user.is_authenticated():
            return cls.objects.none()
        if getattr(user, 'is_superuser', False):
            logger.debug('- superuser granted')
            return cls.objects
        if isinstance(level, basestring):
            level = cls.get_level_object(level)
            logger.debug("- level set by str: %s", unicode(level))

        ct = ContentType.objects.get_for_model(cls)
        ols = user.objectlevel_set.filter(
            Q(users=user) | Q(groups__in=user.groups.all()),
            content_type=ct, level__weight__gte=level.weight).distinct()
        return cls.objects.filter(objectlevel_set__in=ols.all())

    class Meta:
        abstract = True
