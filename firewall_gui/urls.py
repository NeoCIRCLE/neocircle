from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'rules/(?P<id>\d+)/$', 'firewall_gui.views.show_rule'),
    url(r'hosts/(?P<id>\d+)/$', 'firewall_gui.views.show_host'),
    url(r'vlans/(?P<id>\d+)/$', 'firewall_gui.views.show_vlan'),
    url(r'vlangroups/(?P<id>\d+)/$', 'firewall_gui.views.show_vlangroup'),
    url(r'hostgroups/(?P<id>\d+)/$', 'firewall_gui.views.show_hostgroup'),
    url(r'records/(?P<id>\d+)/$', 'firewall_gui.views.show_record'),
    url(r'domains/(?P<id>\d+)/$', 'firewall_gui.views.show_domain'),

    url(r'(?P<name>\w+)/$', 'firewall_gui.views.list_entities'),

    url(r'autocomplete/(?P<entity>\w+)/$', 'firewall_gui.views.autocomplete'),

    url(r'rules/save/$', 'firewall_gui.views.save_rule'),
    url(r'hosts/save/$', 'firewall_gui.views.save_host'),
    url(r'vlans/save/$', 'firewall_gui.views.save_vlan'),
    url(r'vlangroups/save/$', 'firewall_gui.views.save_vlangroup'),
    url(r'hostgroups/save/$', 'firewall_gui.views.save_hostgroup'),
    url(r'domains/save/$', 'firewall_gui.views.save_domain'),
    url(r'records/save/$', 'firewall_gui.views.save_record'),

    url(r'(?P<name>\w+)/(?P<id>\d+)/delete/',
        'firewall_gui.views.delete_entity'),

    url(r'rules/new/$', 'firewall_gui.views.show_rule'),
    url(r'hosts/new/$', 'firewall_gui.views.show_host'),
    url(r'vlans/new/$', 'firewall_gui.views.show_vlan'),
    url(r'vlangroups/new/$', 'firewall_gui.views.show_vlangroup'),
    url(r'hostgroups/new/$', 'firewall_gui.views.show_hostgroup'),
    url(r'domains/new/$', 'firewall_gui.views.show_domain'),
    url(r'records/new/$', 'firewall_gui.views.show_record'),
    # url(r'vlangroups/save/$', 'firewall_gui.views.save_vlangroup'),
    # url(r'hostgroups/save/$', 'firewall_gui.views.save_hostgroup'),
    # url(r'domains/save/$', 'firewall_gui.views.save_domain'),
    # url(r'records/save/$', 'firewall_gui.views.save_record'),

    url(r'$', 'firewall_gui.views.index'),
)
