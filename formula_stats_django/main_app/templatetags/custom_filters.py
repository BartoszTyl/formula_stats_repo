from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replaces all instances of a string with another.
    Usage: {{ value|replace:"old,new" }}
    """
    old, new = arg.split(",")
    return value.replace(old, new)



@register.filter
def index(sequence, position):

    try:
        return sequence[position]
    except:
        return ''