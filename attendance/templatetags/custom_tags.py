from django import template

register = template.Library()

@register.filter
def to_range(value):
    """Return range from 1 to value (inclusive)"""
    try:
        return range(1, int(value)+1)
    except:
        return range(0)
