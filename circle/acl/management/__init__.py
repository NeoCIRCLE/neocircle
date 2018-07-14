"""
Creates Levels for all installed apps that have levels.
"""
from django.db.models import signals
from django.apps import apps
from django.db import DEFAULT_DB_ALIAS
from django.core.exceptions import ImproperlyConfigured

from ..models import Level, AclBase


def create_levels(app_config, verbosity=False, using=DEFAULT_DB_ALIAS,
                  **kwargs):
    """Create and set the weights of the configured Levels.

    Based on django.contrib.auth.management.__init__.create_permissions"""
    # if not router.allow_migrate(using, auth_app.Permission):
    #    return

    from django.contrib.contenttypes.models import ContentType

    app_models = [k for k in apps.get_models(app_config)
                  if AclBase in k.__bases__]
    print "Creating levels for models: %s." % ", ".join(
        [m.__name__ for m in app_models])

    # This will hold the levels we're looking for as
    # (content_type, (codename, name))
    searched_levels = list()
    level_weights = list()
    # The codenames and ctypes that should exist.
    ctypes = set()
    for klass in app_models:
        # Force looking up the content types in the current database
        # before creating foreign keys to them.
        ctype1 = ContentType.objects.db_manager(using).get_for_model(klass)
        ctypes.add(ctype1)
        weight = 0
        try:
            for codename, name in klass.ACL_LEVELS:
                searched_levels.append((ctype1, (codename, name)))
                level_weights.append((ctype1, codename, weight))
                weight += 1
        except AttributeError:
            raise ImproperlyConfigured(
                "Class %s doesn't have ACL_LEVELS attribute." % klass)

    # Find all the Levels that have a content_type for a model we're
    # looking for.  We don't need to check for codenames since we already have
    # a list of the ones we're going to create.
    all_levels = set(Level.objects.using(using).filter(
        content_type__in=ctypes,
    ).values_list(
        "content_type", "codename"
    ))

    levels = [
        Level(codename=codename, name=name, content_type=ctype)
        for ctype, (codename, name) in searched_levels
        if (ctype.pk, codename) not in all_levels
    ]
    Level.objects.using(using).bulk_create(levels)
    if verbosity >= 2:
        print("Adding levels [%s]." % ", ".join(unicode(l) for l in levels))
        print("Searched: [%s]." % ", ".join(
            unicode(l) for l in searched_levels))
        print("All: [%s]." % ", ".join(unicode(l) for l in all_levels))

    # set weights
    for ctype, codename, weight in level_weights:
        Level.objects.filter(codename=codename,
                             content_type=ctype).update(weight=weight)


signals.post_migrate.connect(
    create_levels, dispatch_uid="circle.acl.management.create_levels")
