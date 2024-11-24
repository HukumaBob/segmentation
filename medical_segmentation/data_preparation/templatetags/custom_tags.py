# templatetags/custom_tags.py
from django import template

register = template.Library()

@register.simple_tag
def is_active(request, pattern):
    return 'active' if pattern == request.path else ''
