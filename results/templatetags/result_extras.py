from django import template

register = template.Library()


@register.filter
def dictattr(mapping, key):
    """{{ some_dict|dictattr:variable_key }} — Django's built-in dict.key
    lookup only works for literal keys; this resolves a variable one
    (used by the broadsheet to look up a student's result per subject id)."""
    if not mapping:
        return None
    return mapping.get(key)


@register.filter
def component_value(result, component):
    """{{ result|component_value:component }} — a Result's score for one
    configurable ScoreComponent. Assumes component_scores was prefetched
    (see _report_card_context / the entry grid) so this doesn't issue a
    query per cell."""
    if not result:
        return 0
    match = next((cs for cs in result.component_scores.all() if cs.component_id == component.id), None)
    return match.value if match else 0
