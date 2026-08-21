"""
Thin accessors views use to pull editable copy — keeps views.py from
repeating `PageSection.objects.filter(key=...).first()` everywhere, and
gives every page a safe default so a not-yet-seeded install never 500s.
"""

from website.models import ContentBlock, PageSection


class _EmptySection:
    eyebrow = heading = body = ''
    paragraphs = []


def get_section(key):
    return PageSection.objects.filter(key=key).first() or _EmptySection()


def get_blocks(page, section):
    return ContentBlock.objects.filter(page=page, section=section, is_active=True)
