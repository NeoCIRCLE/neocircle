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
import logging
from django.conf import settings
from django.contrib.auth.models import Group
from .models import GroupProfile, FutureMember, Profile
if getattr(settings, 'LDAP_ORG_ID_ATTRIBUTE', False):
    import ldap
    from django_auth_ldap.backend import LDAPSettings
    from django_auth_ldap.config import LDAPSearch


logger = logging.getLogger(__name__)


def ldap_connect():
    ldap_settings = LDAPSettings()
    conn = ldap.initialize(ldap_settings.SERVER_URI)
    for opt, value in ldap_settings.CONNECTION_OPTIONS.items():
        conn.set_option(opt, value)
    conn.simple_bind_s(ldap_settings.BIND_DN, ldap_settings.BIND_PASSWORD)
    return conn


def get_group(conn, group_dn):
    group = LDAPSearch(group_dn, ldap.SCOPE_BASE, "cn=*").execute(conn)
    if len(group) == 0:
        return None
    return group[0][1]


def get_group_org_id(conn, group_dn):
    group_org_id_attr = settings.LDAP_GROUP_ORG_ID_ATTRIBUTE
    if group_org_id_attr == "DN":
        return group_dn.upper()
    else:
        group = get_group(conn, group_dn)
        if group is None:
            logger.error("LDAP communication error, "
                         "while query group object.")
            return None
        group_org_id = group.get(group_org_id_attr)
        if group_org_id is None:
            logger.error("Group org id attribute '%s' does not exist!",
                         group_org_id_attr)
            return None
        return group_org_id[0].upper()


def get_user_org_id(ldap_user):
    user_org_id_attr = settings.LDAP_USER_ORG_ID_ATTRIBUTE
    if user_org_id_attr == "DN":
        return ldap_user.dn.upper()
    else:
        user_org_id = ldap_user.attrs.get(user_org_id_attr)
        if user_org_id is None:
            logger.error("User org id attribute '%s' does not exist!",
                         user_org_id_attr)
        return user_org_id[0]


def owns(conn, user_dn, group_dn):
    ownerattr = settings.LDAP_GROUP_OWNER_ATTRIBUTE
    group = get_group(conn, group_dn)
    if group is None:
        return False
    owners = group.get(ownerattr, [])
    return user_dn in owners


def ldap_save_org_id(sender, user, ldap_user, **kwargs):
    logger.debug("ldap_save_org_id called by %s", user.username)

    user_org_id = get_user_org_id(ldap_user)
    if user_org_id is None:
        return

    if user.pk is None:
        user.save()
        logger.debug("ldap_save_org_id saved user %s", unicode(user))

    profile, created = Profile.objects.get_or_create(user=user)
    if created or profile.org_id != user_org_id:
        logger.info("org_id of %s added to user %s's profile",
                    user_org_id, user.username)
        profile.org_id = user_org_id
        profile.save()
    else:
        logger.debug("org_id of %s already added to user %s's profile",
                     user_org_id, user.username)

    # connection will close, when object destroys
    # https://www.python-ldap.org/doc/html/ldap.html#ldap-objects
    conn = ldap_connect()
    for group_dn in ldap_user.group_dns:
        group_org_id = get_group_org_id(conn, group_dn)
        if group_org_id is None:
            continue
        try:
            g = GroupProfile.search(group_org_id)
        except Group.DoesNotExist:
            logger.debug('cant find membergroup %s', group_org_id)
        else:
            logger.debug('could find membergroup %s (%s)',
                         group_org_id, unicode(g))
            g.user_set.add(user)

    for i in FutureMember.objects.filter(org_id__iexact=user_org_id):
        i.group.user_set.add(user)
        i.delete()

    for group_dn in ldap_user.group_dns:
        group_org_id = get_group_org_id(conn, group_dn)
        if group_org_id is None:
            continue
        try:
            g = GroupProfile.search(group_org_id)
        except Group.DoesNotExist:
            logger.debug('cant find ownergroup %s', group_org_id)
        else:
            if owns(conn, ldap_user.dn, group_dn):
                logger.debug('could find ownergroup %s (%s)',
                             group_org_id, unicode(g))
                g.profile.set_level(user, 'owner')
            else:
                logger.debug('cant find ownergroup %s', group_org_id)

    return False  # User did not change
