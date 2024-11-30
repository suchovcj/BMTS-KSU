# bmts/templatetags/custom_filters.py
from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def duration(td):
    if not isinstance(td, timedelta):
        return "N/A"
    
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    
    if hours >= 24:
        days = hours // 24
        return f"{days} days"
    return f"{hours} hours"

@register.filter
def absolute(value):  # Changed from 'abs' to 'absolute'
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value