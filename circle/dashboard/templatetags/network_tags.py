from django import template

register = template.Library()


LINKABLE_PORTS = [80, 8080, 443, 8010]


@register.simple_tag(name="display_portforward")
def display_pf(ports):
    is_ipv6 = "ipv6" in ports
    data = ports["ipv6" if is_ipv6 else "ipv4"]

    if ports['private'] in LINKABLE_PORTS:
        href = "%s:%d" % (data['host'], data['port'])
        return '<a href="http://%s">%s</a>' % (href, href)
    return "%s:%d" % (data['host'], data['port'])
