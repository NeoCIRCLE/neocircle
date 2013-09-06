from django.views.generic import TemplateView
from vm.models import Instance


class IndexView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context.update({
            'instances': Instance.objects.filter(owner=self.request.user),
        })
        return context


class VmDetailView(TemplateView):
    template_name = "dashboard/vm-detail.html"
