from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from occi.utils import OcciRequestNotValid


class EnsureCsrfTokenMixin(object):

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(EnsureCsrfTokenMixin, self).dispatch(*args, **kwargs)


class OcciViewMixin(EnsureCsrfTokenMixin):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return OcciRequestNotValid(message="Authentication required.",
                                       status=403).response
        return super(OcciViewMixin, self).dispatch(request, *args, **kwargs)
