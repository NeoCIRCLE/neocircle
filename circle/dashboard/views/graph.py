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

from __future__ import absolute_import, unicode_literals

import logging
import requests

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View

from braces.views import LoginRequiredMixin

from vm.models import Instance, Node, InstanceTemplate


logger = logging.getLogger(__name__)


def register_graph(metric_cls, graph_name, graphview_cls):
    if not hasattr(graphview_cls, 'metrics'):
        graphview_cls.metrics = {}
    graphview_cls.metrics[graph_name] = metric_cls


class GraphViewBase(LoginRequiredMixin, View):
    def create_class(self, cls):
        return type(str(cls.__name__ + 'Metric'), (cls, self.base), {})

    def get(self, request, pk, metric, time, *args, **kwargs):
        graphite_url = settings.GRAPHITE_URL
        if graphite_url is None:
            raise Http404()

        try:
            metric = self.metrics[metric]
        except KeyError:
            raise Http404()

        try:
            instance = self.get_object(request, pk)
        except self.model.DoesNotExist:
            raise Http404()

        metric = self.create_class(metric)(instance)

        return HttpResponse(metric.get_graph(graphite_url, time),
                            content_type="image/png")

    def get_object(self, request, pk):
        instance = self.model.objects.get(id=pk)
        if not instance.has_level(request.user, 'user'):
            raise PermissionDenied()
        return instance


class Metric(object):
    cacti_style = True
    derivative = False
    scale_to_seconds = None
    metric_name = None
    title = None
    label = None

    def __init__(self, obj, metric_name=None):
        self.obj = obj
        self.metric_name = (
            metric_name or self.metric_name or self.__class__.__name__.lower())

    def get_metric_name(self):
        return self.metric_name

    def get_label(self):
        return self.label or self.get_metric_name()

    def get_title(self):
        return self.title or self.get_metric_name()

    def get_minmax(self):
        return (None, None)

    def get_target(self):
        target = '%s.%s' % (self.obj.metric_prefix, self.get_metric_name())
        if self.derivative:
            target = 'nonNegativeDerivative(%s)' % target
        if self.scale_to_seconds:
            target = 'scaleToSeconds(%s, %d)' % (target, self.scale_to_seconds)
        target = 'alias(%s, "%s")' % (target, self.get_label())
        if self.cacti_style:
            target = 'cactiStyle(%s)' % target
        return target

    def get_graph(self, graphite_url, time, width=500, height=200):
        params = {'target': self.get_target(),
                  'from': '-%s' % time,
                  'title': self.get_title().encode('UTF-8'),
                  'width': width,
                  'height': height}

        ymin, ymax = self.get_minmax()
        if ymin is not None:
            params['yMin'] = ymin
        if ymax is not None:
            params['yMax'] = ymax

        logger.debug('%s %s', graphite_url, params)
        response = requests.get('%s/render/' % graphite_url, params=params)
        return response.content


class VmMetric(Metric):
    def get_title(self):
        title = super(VmMetric, self).get_title()
        return '%s (%s) - %s' % (self.obj.name, self.obj.vm_name, title)


class NodeMetric(Metric):
    def get_title(self):
        title = super(NodeMetric, self).get_title()
        return '%s (%s) - %s' % (self.obj.name, self.obj.host.hostname, title)


class VmGraphView(GraphViewBase):
    model = Instance
    base = VmMetric


class NodeGraphView(GraphViewBase):
    model = Node
    base = NodeMetric

    def get_object(self, request, pk):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return self.model.objects.get(id=pk)


class TemplateGraphView(GraphViewBase):
    model = InstanceTemplate
    base = Metric

    def get_object(self, request, pk):
        instance = super(TemplateGraphView, self).get_object(request, pk)
        if not instance.has_level(request.user, 'operator'):
            raise PermissionDenied()
        return instance


class TemplateVms(object):
    metric_name = "instances.running"
    title = _("Instance count")
    label = _("instance count")

    def get_minmax(self):
        return (0, None)


register_graph(TemplateVms, 'instances', TemplateGraphView)


class NodeListGraphView(GraphViewBase):
    model = Node
    base = Metric

    def get_object(self, request, pk):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return Node.objects.filter(enabled=True)

    def get(self, request, metric, time, *args, **kwargs):
        if not self.request.user.has_perm('vm.view_statistics'):
            raise PermissionDenied()
        return super(NodeListGraphView, self).get(request, None, metric, time)


class Ram(object):
    metric_name = "memory.usage"
    title = _("RAM usage (%)")
    label = _("RAM usage (%)")

    def get_minmax(self):
        return (0, 105)


register_graph(Ram, 'memory', VmGraphView)
register_graph(Ram, 'memory', NodeGraphView)


class Cpu(object):
    metric_name = "cpu.percent"
    title = _("CPU usage (%)")
    label = _("CPU usage (%)")

    def get_minmax(self):
        if isinstance(self.obj, Node):
            return (0, 105)
        else:
            return (0, self.obj.num_cores * 100 + 5)


register_graph(Cpu, 'cpu', VmGraphView)
register_graph(Cpu, 'cpu', NodeGraphView)


class VmNetwork(object):
    title = _("Network")

    def get_minmax(self):
        return (0, None)

    def get_target(self):
        metrics = []
        for n in self.obj.interface_set.all():
            params = (self.obj.metric_prefix, n.vlan.vid, n.vlan.name)
            metrics.append(
                'alias(scaleToSeconds(nonNegativeDerivative('
                '%s.network.bytes_recv-%s), 10), "out - %s (bits/s)")' % (
                    params))
            metrics.append(
                'alias(scaleToSeconds(nonNegativeDerivative('
                '%s.network.bytes_sent-%s), 10), "in - %s (bits/s)")' % (
                    params))
        return 'group(%s)' % ','.join(metrics) if metrics else None


register_graph(VmNetwork, 'network', VmGraphView)


class NodeNetwork(object):
    title = _("Network")

    def get_minmax(self):
        return (0, None)

    def get_target(self):
        return (
            'aliasSub(scaleToSeconds(nonNegativeDerivative(%s.network.b*),'
            '10), ".*\.bytes_(sent|recv)-([a-zA-Z0-9]+).*", "\\2 \\1")' % (
                self.obj.metric_prefix))


register_graph(NodeNetwork, 'network', NodeGraphView)


class NodeVms(object):
    metric_name = "vmcount"
    title = _("Instance count")
    label = _("instance count")

    def get_minmax(self):
        return (0, None)


register_graph(NodeVms, 'vm', NodeGraphView)


class NodeAllocated(object):
    title = _("Allocated memory (bytes)")

    def get_target(self):
        prefix = self.obj.metric_prefix
        if self.obj.online and self.obj.enabled:
            ram_size = self.obj.ram_size
        else:
            ram_size = 0
        used = 'alias(%s.memory.used_bytes, "used")' % prefix
        allocated = 'alias(%s.memory.allocated, "allocated")' % prefix
        max = 'threshold(%d, "max")' % ram_size
        return 'cactiStyle(group(%s, %s, %s))' % (used, allocated, max)

    def get_minmax(self):
        return (0, None)


register_graph(NodeAllocated, 'alloc', NodeGraphView)


class NodeListAllocated(object):
    title = _("Allocated memory (bytes)")

    def get_target(self):
        nodes = self.obj
        used = ','.join('%s.memory.used_bytes' % n.metric_prefix
                        for n in nodes)
        allocated = 'alias(sumSeries(%s), "allocated")' % ','.join(
            '%s.memory.allocated' % n.metric_prefix for n in nodes)
        max = 'threshold(%d, "max")' % sum(
            n.ram_size for n in nodes if n.online)
        return ('group(aliasSub(aliasByNode(stacked(group(%s)), 1), "$",'
                '"  (used)"), %s, %s)' % (used, allocated, max))

    def get_minmax(self):
        return (0, None)


register_graph(NodeListAllocated, 'alloc', NodeListGraphView)


class NodeListVms(object):
    title = _("Instance count")

    def get_target(self):
        vmcount = ','.join('%s.vmcount' % n.metric_prefix for n in self.obj)
        return 'group(aliasByNode(stacked(group(%s)), 1))' % vmcount

    def get_minmax(self):
        return (0, None)


register_graph(NodeListVms, 'vm', NodeListGraphView)
