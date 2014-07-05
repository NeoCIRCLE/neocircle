from django import template

register = template.Library()


LINKABLE_PORTS = {80: "http", 8080: "http", 443: "https", 21: "ftp"}


@register.simple_tag(name="display_portforward4")
def display_pf4(ports):
    return display_pf(ports, 'ipv4')


@register.simple_tag(name="display_portforward6")
def display_pf6(ports):
    return display_pf(ports, 'ipv6')


def display_pf(ports, proto):
    data = ports[proto]

    if ports['private'] in LINKABLE_PORTS.keys():
        href = "%s:%d" % (data['host'], data['port'])
        return '<a href="%s://%s">%s</a>' % (
            LINKABLE_PORTS.get(ports['private']), href, href)
    return "%s:%d" % (data['host'], data['port'])
