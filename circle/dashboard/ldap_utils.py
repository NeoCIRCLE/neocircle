import logging
from django.conf import settings
from django.contrib.auth.models import Group
from .models import GroupProfile, FutureMember, Profile
import ldap
from django_auth_ldap.backend import LDAPSettings


logger = logging.getLogger(__name__)


def ldap_connect(ldap_settings):
    conn = ldap.initialize(ldap_settings.SERVER_URI)
    for opt, value in ldap_settings.CONNECTION_OPTIONS.items():
        conn.set_option(opt, value)
    conn.simple_bind_s(ldap_settings.BIND_DN, ldap_settings.BIND_PASSWORD)
    return conn


def owns(conn, ldap_settings, ownerattr, user_dn, group_name):
    group = ldap_settings.GROUP_SEARCH.search_with_additional_term_string(
        "(cn=%s)" % group_name).execute(conn)
    if len(group) == 0:
        return False
    group = group[0]
    owners = group[1].get(ownerattr, [])
    return user_dn in map(unicode.upper, owners)


def ldap_save_org_id(sender, user, ldap_user, **kwargs):
    logger.debug("ldap_save_org_id called by %s", user.username)
    user_dn = ldap_user.dn.upper()

    if user.pk is None:
        user.save()
        logger.debug("ldap_save_org_id saved user %s", unicode(user))

    profile, created = Profile.objects.get_or_create(user=user)
    if created or profile.org_id != user_dn:
        logger.info("org_id of %s added to user %s's profile",
                    user_dn, user.username)
        profile.org_id = user_dn
        profile.save()
    else:
        logger.debug("org_id of %s already added to user %s's profile",
                     user_dn, user.username)

    group_dns = map(unicode.upper, ldap_user.group_dns)
    for group in group_dns:
        try:
            g = GroupProfile.search(group)
        except Group.DoesNotExist:
            logger.debug('cant find membergroup %s', group)
        else:
            logger.debug('could find membergroup %s (%s)',
                         group, unicode(g))
            g.user_set.add(user)

    for i in FutureMember.objects.filter(org_id__iexact=user_dn):
        i.group.user_set.add(user)
        i.delete()

    ownerattr = settings.LDAP_GROUP_OWNER_ATTRIBUTE
    ldap_settings = LDAPSettings()
    # connection will close, when object destroys
    # https://www.python-ldap.org/doc/html/ldap.html#ldap-objects
    conn = ldap_connect(ldap_settings)
    for group in zip(group_dns, ldap_user.group_names):
        try:
            g = GroupProfile.search(group[0])
        except Group.DoesNotExist:
            logger.debug('cant find ownergroup %s', group[0])
        else:
            if owns(conn, ldap_settings, ownerattr, user_dn, group[1]):
                logger.debug('could find ownergroup %s (%s)',
                             group[0], unicode(g))
                g.profile.set_level(user, 'owner')
            else:
                logger.debug('cant find ownergroup %s', group[0])

    return False  # User did not change
