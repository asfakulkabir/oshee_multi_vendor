from collections import defaultdict
from products.models import Category

def mega_menu_categories(request):
    parent_categories = Category.objects.filter(parent__isnull=True)
    structured_mega_menu = {}

    for parent in parent_categories:
        grouped = defaultdict(list)
        for child in parent.children.all():
            group = child.group_name or "Other"
            grouped[group].append(child)

            for grandchild in child.children.all():
                grouped[group].append(grandchild)

        structured_mega_menu[parent.id] = dict(grouped)

    return {
        'parent_categories': parent_categories,
        'structured_mega_menu': structured_mega_menu,
    }

def all_categories(request):
    footer_categories = Category.objects.filter()
    return {
        'footer_categories': footer_categories,
    }

