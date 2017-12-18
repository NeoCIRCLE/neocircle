from rest_framework import viewsets
from . import serializers
from firewall import models


class RelativeURLFieldMixin(object):
    def get_serializer_context(self):
        context = super(RelativeURLFieldMixin, self).get_serializer_context()
        context['request'] = None
        return context


class BlacklistViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.BlacklistItem.objects.all()
    serializer_class = serializers.BlacklistItemSerializer


class DomainViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Domain.objects.all()
    serializer_class = serializers.DomainSerializer


class FirewallViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Firewall.objects.all()
    serializer_class = serializers.FirewallSerializer


class GroupViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Group.objects.all()
    serializer_class = serializers.GroupSerializer


class HostViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Host.objects.all()
    serializer_class = serializers.HostSerializer


class RecordViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Record.objects.all()
    serializer_class = serializers.RecordSerializer


class RuleViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Rule.objects.all()
    serializer_class = serializers.RuleSerializer


class SwitchPortViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.SwitchPort.objects.all()
    serializer_class = serializers.SwitchPortSerializer


class VlanViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.Vlan.objects.all()
    serializer_class = serializers.VlanSerializer


class VlanGroupViewSet(RelativeURLFieldMixin, viewsets.ModelViewSet):
    queryset = models.VlanGroup.objects.all()
    serializer_class = serializers.VlanGroupSerializer
