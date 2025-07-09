# your_app/templatetags/shop_tags.py

from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def modify_query(context, **kwargs):

    request = context['request']
    params = request.GET.copy()

    for key, value in kwargs.items():
        if value is None:
            if key in params:
                del params[key]
        else:
            params[key] = value
    
    # Ensure 'page' is reset if other filters change
    if any(k not in ['page'] for k in kwargs.keys()):
        if 'page' in params:
            del params['page']

    return params.urlencode()