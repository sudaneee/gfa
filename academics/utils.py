from academics.models import Section


def sections_for_user(user):
    """
    Admins see every section; teachers see only the sections they're
    assigned to (staff.Teacher.sections). Used to scope the class picker on
    the attendance/results entry screens.
    """
    if user.role == 'admin':
        return Section.objects.select_related('school_class').all()
    teacher = getattr(user, 'teacher_profile', None)
    if not teacher:
        return Section.objects.none()
    return teacher.sections.select_related('school_class').all()
