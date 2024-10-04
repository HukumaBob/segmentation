import hashlib
from django import template

register = template.Library()

@register.filter
def generate_color(value):
    """
    Генерация цвета на основе хеширования входного значения.
    """
    # Преобразуем значение в хеш и берем первые 6 символов для HEX-кода
    hex_color = hashlib.md5(value.encode()).hexdigest()[:6]
    return f"#{hex_color}"
