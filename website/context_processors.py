from website.models import SchoolSettings


def school_settings(request):
    """Makes `{{ school }}` available in every template (base.html's navbar/footer)."""
    return {'school': SchoolSettings.get_solo()}
