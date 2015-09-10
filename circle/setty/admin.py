from django.contrib import admin
from .models import (
    Element,
    ElementTemplate,
    ElementConnection,
    Service,
)

admin.site.register(Element)
admin.site.register(ElementTemplate)
admin.site.register(ElementConnection)
admin.site.register(Service)
