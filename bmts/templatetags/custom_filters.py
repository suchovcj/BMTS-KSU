# bmts/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def absolute(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value