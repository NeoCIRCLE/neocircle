from django.template import Library


register = Library()


@register.filter
def get_text(human_readable, user):
    if human_readable is None:
        return u""
    else:
        return human_readable.get_text(user)
