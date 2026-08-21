"""Small helpers shared by the generic list/form views."""


def resolve_value(obj, attr_path):
    """Resolve a dotted attribute path (e.g. 'school_class') or plain
    property/field name off a model instance, for list_fields rendering."""
    value = obj
    for part in attr_path.split('.'):
        value = getattr(value, part, None)
        if value is None:
            return None
    return value


def querystring_without_page(request):
    """The current GET querystring minus `page`, with a trailing '&' when
    non-empty, so pagination links can just do `?{{ querystring }}page=N`."""
    params = request.GET.copy()
    params.pop('page', None)
    encoded = params.urlencode()
    return f'{encoded}&' if encoded else ''


def filter_options(model, field_name):
    """(value, label) pairs for one filter <select> — model choices for a
    CharField-with-choices, the related queryset for a ForeignKey, or
    Yes/No for a BooleanField."""
    django_field = model._meta.get_field(field_name)
    if getattr(django_field, 'choices', None):
        return list(django_field.choices)
    if django_field.get_internal_type() == 'BooleanField':
        return [('True', 'Yes'), ('False', 'No')]
    if django_field.is_relation:
        return [(obj.pk, str(obj)) for obj in django_field.related_model.objects.all()]
    return []


def filter_lookup_value(model, field_name, raw_value):
    """Coerce a filter <select>'s raw GET-param string into whatever
    .filter(**{field_name: ...}) actually needs — a BooleanField in
    particular must not receive the literal string "False" (which Python
    treats as truthy and would silently match every row)."""
    if model._meta.get_field(field_name).get_internal_type() == 'BooleanField':
        return raw_value == 'True'
    return raw_value
