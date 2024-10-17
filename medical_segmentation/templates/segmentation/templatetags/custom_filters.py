import os
from django import template

register = template.Library()

@register.filter
def filename(value):
    """Возвращает только имя файла из полного пути."""
    return os.path.basename(value)