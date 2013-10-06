from django.core.urlresolvers import reverse

from guardian.shortcuts import (get_users_with_perms, get_groups_with_perms,
                                get_perms, remove_perm, assign_perm)


def split(t, at):
    """
    Split collection at first occurance of given element.

    >>> split("FooBar", "B")
    ('Foo', 'Bar')
    >>> split(range(5), 2)
    ([0, 1], [2, 3, 4])
    """

    pos = t.index(at)
    return t[:pos], t[pos:]


def first_common_element(a, b):
    for i in a:
        if i in b:
            return i
    return None


def get_acl_data(obj):
    levels = obj._meta.permissions
    levelids = [id for (id, name) in levels]
    users = get_users_with_perms(obj, with_group_users=False)
    users = [{'user': u,
              'perm': first_common_element(levelids, get_perms(u, obj))}
             for u in users]
    groups = get_groups_with_perms(obj)
    groups = [{'group': g,
               'perm': first_common_element(levelids, get_perms(g, obj))}
              for g in groups]
    return {'users': users, 'groups': groups, 'levels': levels,
            'url': reverse('dashboard.views.vm-acl', args=[obj.pk])}


def set_acl_level(obj, whom, level):
    levels = obj._meta.permissions
    levelids = [id for (id, name) in levels]
    to_remove, to_add = split(levelids, level)
    for p in to_remove:
        remove_perm(p, whom, obj)
    for p in to_add:
        assign_perm(p, whom, obj)
