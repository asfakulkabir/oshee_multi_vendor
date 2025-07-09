from django import template
from urllib.parse import urlencode

register = template.Library()

@register.simple_tag(takes_context=True)
def modify_query(context, **kwargs):
    request = context['request']
    params = request.GET.copy()

    if any(k != 'page' and k in kwargs for k in kwargs):
        if 'page' in params:
            del params['page']

    for key, value in kwargs.items():
        if value is None:
            if key in params:
                del params[key]
        elif isinstance(value, list):
            if key in params:
                del params[key]
            for item in value:
                params.appendlist(key, str(item))
        else:
            params[key] = str(value)
            
    final_params = []
    for key, val_list in params.lists():
        for val in val_list:
            final_params.append((key, val))

    return urlencode(final_params)