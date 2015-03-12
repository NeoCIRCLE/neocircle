
from django.utils.translation import ugettext_lazy as _

from django_tables2 import Table, A
from django_tables2.columns import (
    TemplateColumn, LinkColumn
)

from request.models import Request, LeaseType, TemplateAccessType


class RequestTable(Table):
    pk = LinkColumn(
        'request.views.request-detail',
        args=[A('pk')],
        verbose_name=_("ID"),
    )

    class Meta:
        model = Request
        attrs = {'class': ('table table-bordered table-striped table-hover'),
                 'id': "request-list-table"}
        fields = ("pk", "status", "type", "user", )
        order_by = ("-pk", )
        empty_text = _("No more requests.")


class LeaseTypeTable(Table):
    pk = LinkColumn(
        'request.views.lease-type-detail',
        args=[A('pk')],
        verbose_name=_("ID"),
    )

    class Meta:
        model = LeaseType
        attrs = {'class': "table table-bordered table-striped table-hover"}
        fields = ('pk', 'name', 'lease', )
        prefix = "lease-"
        template = "django_tables2/with_pagination.html"


class TemplateAccessTypeTable(Table):
    pk = LinkColumn(
        'request.views.template-type-detail',
        args=[A('pk')],
        verbose_name=_("ID"),
    )
    templates = TemplateColumn(
        template_name="request/columns/templates.html",
        verbose_name=_("Templates"),
    )

    class Meta:
        model = TemplateAccessType
        attrs = {'class': "table table-bordered table-striped table-hover"}
        fields = ('pk', 'name', 'templates', )
        prefix = "template-"
        template = "django_tables2/with_pagination.html"
