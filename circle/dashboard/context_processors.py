from django.conf import settings


def notifications(request):
    count = (request.user.notification_set.filter(status="new").count()
             if request.user.is_authenticated() else None)
    return {
        'NEW_NOTIFICATIONS_COUNT': count
    }


def extract_settings(request):
    return {
        'COMPANY_NAME': getattr(settings, "COMPANY_NAME", None),
    }