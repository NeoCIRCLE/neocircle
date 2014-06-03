from django import template

register = template.Library()


LINKABLE_PORTS = {80: "http", 8080: "http", 443: "https", 21: "ftp"}


@register.simple_tag(name="display_portforward")
def display_pf(ports):
    is_ipv6 = "ipv6" in ports
    data = ports["ipv6" if is_ipv6 else "ipv4"]

    if ports['private'] in LINKABLE_PORTS.keys():
        href = "%s:%d" % (data['host'], data['port'])
        return '<a href="%s://%s">%s</a>' % (
            LINKABLE_PORTS.get(ports['private']), href, href)
    return "%s:%d" % (data['host'], data['port'])
