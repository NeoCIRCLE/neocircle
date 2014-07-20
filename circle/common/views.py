from sys import exc_info

import logging

from django.template import RequestContext
from django.shortcuts import render_to_response

from .models import HumanReadableException

logger = logging.getLogger(__name__)


def handler500(request):
    cls, exception, traceback = exc_info()
    logger.exception("unhandled exception")
    ctx = {}
    if isinstance(exception, HumanReadableException):
        try:
            ctx['error'] = exception.get_user_text()
        except:
            pass
        else:
            try:
                if request.user.is_superuser():
                    ctx['error'] = exception.get_admin_text()
            except:
                pass
        try:
            resp = render_to_response("500.html", ctx, RequestContext(request))
        except:
            resp = render_to_response("500.html", ctx)
        resp.status_code = 500
        return resp
