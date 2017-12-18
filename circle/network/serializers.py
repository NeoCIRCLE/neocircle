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

from rest_framework import serializers

from firewall import models


class BlacklistItemSerializer(serializers.HyperlinkedModelSerializer):
    host_name = serializers.SerializerMethodField()

    class Meta:
        model = models.BlacklistItem
        fields = (
            "url", "ipv4", "host", "host_name", "expires_at", "whitelisted",
            "reason", "snort_message", "created_at",
        )

    def get_host_name(self, obj):
        if obj.host is None:
            return ''
        return obj.host.hostname


class DomainSerializer(serializers.HyperlinkedModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Domain
        fields = ("url", "name", "ttl", "owner", "owner_name")

    def get_owner_name(self, obj):
        return obj.owner.get_full_name()


class FirewallSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Firewall
        fields = ("url", "name", )


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Group
        fields = ("url", "name", "description", "owner", "owner_name")

    def get_owner_name(self, obj):
        if obj.owner is None:
            return ''
        return obj.owner.get_full_name()

class HostSerializer(serializers.HyperlinkedModelSerializer):
    owner_name = serializers.SerializerMethodField()
    vlan_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Host
        fields = (
            "url",
            "hostname", "reverse", "mac", "vlan", "vlan_name",
            "shared_ip", "ipv4", "ipv6", "external_ipv4",
            "description", "location", "comment", "owner",
            "owner_name", "created_at",
        )

    def get_owner_name(self, obj):
        return obj.owner.get_full_name()

    def get_vlan_name(self, obj):
        return obj.vlan.name


class RecordSerializer(serializers.HyperlinkedModelSerializer):
    owner_name = serializers.SerializerMethodField()
    host_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Record
        fields = (
            "url",
            "type", "host", "host_name", "name", "domain", "address", "ttl",
            "description", "owner", "owner_name", "fqdn",
        )

    def get_owner_name(self, obj):
        return obj.owner.get_full_name()

    def get_host_name(self, obj):
        return obj.host.hostname


class RuleSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Rule
        fields = (
            "url",
            "direction", "description", "foreign_network", "dport",
            "sport", "weight", "proto", "extra", "action", "owner",
            "nat", "nat_external_port", "nat_external_ipv4", "vlan",
            "vlangroup", "host", "hostgroup", "firewall",
        )


class SwitchPortSerializer(serializers.HyperlinkedModelSerializer):
    untagged_vlan_info = serializers.SerializerMethodField()
    tagged_vlans_name = serializers.SerializerMethodField()

    class Meta:
        model = models.SwitchPort
        fields = ("url", "untagged_vlan", "tagged_vlans", "description", "untagged_vlan_info", "tagged_vlans_name")

    def get_untagged_vlan_info(self, obj):
        return '{}'.format(obj.untagged_vlan)

    def get_tagged_vlans_name(self, obj):
        return obj.tagged_vlans.name

class VlanSerializer(serializers.HyperlinkedModelSerializer):
    domain_name = serializers.SerializerMethodField()

    class Meta:
        model = models.Vlan
        fields = (
            "url",
            "name", "vid", "network_type", "managed", "network4",
            "snat_to", "snat_ip", "dhcp_pool", "network6",
            "ipv6_template", "host_ipv6_prefixlen", "domain", "domain_name",
            "reverse_domain", "description", "comment", "owner",
        )

    def get_domain_name(self, obj):
        return obj.domain.name


class VlanGroupSerializer(serializers.HyperlinkedModelSerializer):
    owner_name = serializers.SerializerMethodField()
    class Meta:
        model = models.VlanGroup
        fields = ("url", "name", "vlans", "description", "owner", "owner_name")

    def get_owner_name(self, obj):
        if obj.owner is None:
            return ''
        return obj.owner.get_full_name()
