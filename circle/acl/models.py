from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.generic import (
    GenericForeignKey, GenericRelation
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import (
    ManyToManyField, ForeignKey, CharField, Model, IntegerField
)


class Level(Model):

    """Definition of a permission level.

    Instances are automatically populated based on AclBase.."""
    name = CharField('name', max_length=50)
    content_type = ForeignKey(ContentType)
    codename = CharField('codename', max_length=100)
    weight = IntegerField('weight', null=True)

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

    class Meta:
        unique_together = (('content_type', 'object_id', 'level'),)


class AclBase(Model):

    """Define permission levels for Users/Groups per object."""
    object_level_set = GenericRelation(ObjectLevel)

    def get_level_object(self, level):
        ct = ContentType.objects.get_for_model(self)
        return Level.objects.get(codename=level, content_type=ct)

    def set_level(self, whom, level):
        if isinstance(whom, User):
            self.set_user_level(whom, level)
        elif isinstance(whom, Group):
            self.set_group_level(whom, level)
        else:
            raise AttributeError("Whom must be a User or Group object.")

    def set_user_level(self, user, level):
        if isinstance(level, basestring):
            level = self.get_level_object(level)
        if not self.object_level_set.filter(level_id=level.pk).exists():
            self.object_level_set.create(level=level)
        for i in self.object_level_set.all():
            if i.level_id != level.pk:
                i.users.remove(user)
            else:
                i.users.add(user)
            i.save()

    def set_group_level(self, group, level):
        if isinstance(level, basestring):
            level = self.get_level_object(level)
        #self.object_level_set.get_or_create(level=level, content_object=self)
        if not self.object_level_set.filter(level_id=level.pk).exists():
            self.object_level_set.create(level=level)
        for i in self.object_level_set.all():
            if i.level_id != level.pk:
                i.groups.remove(group)
            else:
                i.groups.add(group)
            i.save()

    def has_level(self, user, level, group_also=True):
        if isinstance(level, basestring):
            level = self.get_level_object(level)

        object_levels = self.object_level_set.filter(
            level__weight__gte=level.weight).all()
        if group_also:
            try:
                groups = user.group_set.values_list('id', flat=True)
            except AttributeError:
                pass  # e.g. AnyonymousUser doesn't have group_set
            else:
                for i in object_levels:
                    if i.users.filter(pk=user.pk).exists():
                        return True
                    if (group_also and
                            i.groups.filter(pk__in=groups).exists()):
                        return True
        return False

    def get_users_with_level(self):
        object_levels = (self.object_level_set.select_related(
            'users', 'level').all())
        users = []
        for object_level in object_levels:
            name = object_level.level.codename
            users.extend([(u, name) for u in object_level.users.all()])
        return users

    def get_groups_with_level(self):
        object_levels = (self.object_level_set.select_related(
            'groups', 'level').all())
        groups = []
        for object_level in object_levels:
            name = object_level.level.codename
            groups.extend([(g, name) for g in object_level.groups.all()])
        return groups

    class Meta:
        abstract = True
