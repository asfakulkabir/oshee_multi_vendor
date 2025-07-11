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


@register.filter
def mask_name(full_name):
    if not full_name:
        return ""
    
    # Split the name into parts (handling first and last names)
    parts = full_name.split()
    
    # Get the first letter of the first name part
    first_initial = parts[0][0] if parts else ""
    
    # Get the last letter of the last name part (if multiple parts exist, 
    # otherwise use the first part's last letter)
    if len(parts) > 1:
        last_initial = parts[-1][-1]
    else:
        last_initial = first_initial # Or handle as needed if only a single name is provided

    # Construct the masked name using 5 asterisks for consistency
    return f"{first_initial}*****{last_initial}"