"""
One-time seed of the exact copy the public site already showed as hardcoded
HTML, into PageSection/ContentBlock rows — so switching the templates over
to database-driven content is a pure refactor with zero visible change on
day one, and every word becomes editable from the Superadmin Console from
then on.

Deliberately NOT wired into reset_demo_data: this is real site content the
school will edit going forward, not demo/test data to be wiped on request.
Safe to re-run (get_or_create, only fills in rows that don't exist yet).
"""

from django.core.management.base import BaseCommand

from website.models import ContentBlock, PageSection

SECTIONS = [
    dict(key='home_welcome', page='home', label='Homepage — Welcome Intro',
         eyebrow='Welcome', heading='Building Future Leaders Since Day One',
         body='Glittering Field Academy is a full-service school in Suleja, Niger State, offering Creche, '
              'Pre-Nursery, Nursery, Primary and Secondary education. We combine strong academics with moral '
              'formation, discipline and modern technology to raise well-rounded leaders of tomorrow.'),
    dict(key='home_moral', page='home', label='Homepage — Academics & Morality',
         eyebrow='Moral & Character Development', heading='Academics and Morality, In Equal Measure',
         body='At Glittering Field Academy, we believe true excellence combines strong academic performance '
              'with sound moral character. Our daily routines, mentorship and enrichment programmes are '
              'designed to raise disciplined, respectful and God-fearing leaders.'),
    dict(key='home_parent_portal', page='home', label='Homepage — Parent Partnership',
         eyebrow='Parent Partnership', heading='We Grow Together With Parents',
         body="A dedicated Parent Portal keeps you connected to your child's academic journey — results, "
              'attendance, fees and announcements, all in one place.'),
    dict(key='about_who_we_are', page='about', label='About — Who We Are',
         eyebrow='Who We Are', heading='A School Built on Excellence and Character',
         body='Glittering Field Academy offers a complete educational journey from Creche through Secondary '
              'School, combining rigorous academics with strong moral and leadership formation.\n'
              'Our classrooms are spacious and well-ventilated, our teachers are dedicated professionals, and '
              'our environment is secured with round-the-clock CCTV monitoring — giving parents confidence '
              'and peace of mind.'),
]

BLOCKS = {
    ('home', 'why_choose_us'): [
        ('fa-solid fa-hands-praying', 'Moral Upbringing', 'A strong foundation of values, discipline and character built alongside academics.'),
        ('fa-solid fa-people-line', 'Leadership Development', 'Programmes designed to raise confident, responsible young leaders.'),
        ('fa-solid fa-futbol', 'Extracurricular Activities', 'Debate, art, sports, quiz and reading clubs that build well-rounded students.'),
        ('fa-solid fa-laptop-code', 'ICT & Digital Learning', 'Modern computer lab and digital tools integrated into everyday learning.'),
    ],
    ('home', 'levels'): [
        ('fa-solid fa-baby', 'Creche', 'Nurturing care and sensory development.'),
        ('fa-solid fa-shapes', 'Pre-Nursery', 'Early learning through play and discovery.'),
        ('fa-solid fa-puzzle-piece', 'Nursery', 'Building a strong foundation for learning.'),
        ('fa-solid fa-book', 'Primary', 'Nurturing young minds for academic excellence.'),
        ('fa-solid fa-graduation-cap', 'Secondary', 'Preparing students for leadership and global impact.'),
    ],
    ('home', 'facilities'): [
        ('fa-solid fa-chalkboard', 'Spacious Classrooms', 'Bright, well-ventilated classrooms designed for focused learning.'),
        ('fa-solid fa-computer', 'Computer Lab', 'Modern computers for hands-on ICT and digital learning.'),
        ('fa-solid fa-flask-vial', 'Science Lab', 'Equipped laboratory for practical science experiments.'),
        ('fa-solid fa-book', 'Library', 'A quiet resource centre stocked with age-appropriate books.'),
        ('fa-solid fa-person-running', 'Playground', 'Safe outdoor space for play, sports and recreation.'),
        ('fa-solid fa-video', 'CCTV Security', 'Round-the-clock camera surveillance for student safety.'),
    ],
    ('home', 'character'): [
        ('fa-solid fa-shield-halved', 'Discipline', 'Clear, fair standards of conduct.'),
        ('fa-solid fa-heart', 'Character', 'Values that last a lifetime.'),
    ],
    ('about', 'stats'): [
        ('fa-solid fa-users', '500+ Students', 'A thriving learning community.'),
        ('fa-solid fa-chalkboard-user', 'Qualified Staff', 'Experienced, caring educators.'),
        ('fa-solid fa-award', 'Approved Curriculum', 'WAEC, NECO, NBAIS approved.'),
        ('fa-solid fa-shield-halved', 'Safe Environment', 'CCTV secured campus.'),
    ],
    ('about', 'mission_vision'): [
        ('fa-solid fa-bullseye', 'Our Mission', 'To provide a nurturing environment where every child receives excellent academic training rooted in strong moral values, preparing them to lead with integrity.'),
        ('fa-solid fa-eye', 'Our Vision', 'To be a leading academy renowned for producing disciplined, academically excellent and globally competitive leaders from Suleja and beyond.'),
        ('fa-solid fa-star', 'Core Values', 'Excellence, Discipline, Integrity, Leadership, Innovation and Compassion guide everything we do, in and out of the classroom.'),
    ],
    ('about', 'philosophy'): [
        ('fa-solid fa-hands-praying', 'Academics & Morality', 'We believe knowledge without character is incomplete — every lesson is paired with values instruction.'),
        ('fa-solid fa-people-line', 'Leadership Development', 'Prefectship, clubs and mentorship programmes build confident, responsible young leaders.'),
        ('fa-solid fa-shield-halved', 'Discipline & Character', 'Clear, fair standards of conduct reinforce respect, responsibility and self-control.'),
        ('fa-solid fa-laptop-code', 'ICT & Digital Learning', 'Our Computer Lab equips students with digital skills essential for the modern world.'),
        ('fa-solid fa-handshake', 'Parent Partnership', 'An online Parent Portal keeps families closely connected to their child\'s progress.'),
        ('fa-solid fa-building-columns', 'Modern Facilities', 'Classrooms, labs, library and playground designed for holistic development.'),
    ],
    ('facilities', 'facilities'): [
        ('fa-solid fa-chalkboard', 'Spacious Classrooms', 'Bright, comfortable classrooms designed for focused learning at every level.'),
        ('fa-solid fa-computer', 'Computer Lab', 'Modern systems supporting ICT and digital learning from an early age.'),
        ('fa-solid fa-flask-vial', 'Science Lab', 'A fully equipped laboratory for hands-on science experiments.'),
        ('fa-solid fa-book', 'Library', 'A quiet, well-stocked space that nurtures a love for reading.'),
        ('fa-solid fa-person-running', 'Playground', 'Ample outdoor space for play, games and physical development.'),
        ('fa-solid fa-video', 'CCTV Security', '24-hour camera surveillance across the school premises.'),
        ('fa-solid fa-bus', 'Transport Services', 'Reliable pick-up and drop-off services within Suleja and environs.'),
        ('fa-solid fa-utensils', 'Feeding Programme', 'Healthy, supervised meals for our Creche and Nursery pupils.'),
        ('fa-solid fa-house-medical', 'First Aid & Care', "On-site care to support students' health and wellbeing."),
    ],
    ('facilities', 'activities'): [
        ('fa-solid fa-people-arrows', 'Debate', 'Building confidence and critical thinking through public speaking.'),
        ('fa-solid fa-palette', 'Art', 'Creative expression through drawing, painting and craft.'),
        ('fa-solid fa-futbol', 'Sports', 'Football, athletics and inter-house sporting competitions.'),
        ('fa-solid fa-brain', 'Quiz Club', 'Sharpening knowledge and quick thinking through friendly competition.'),
        ('fa-solid fa-book-open-reader', 'Reading Club', 'Cultivating a lifelong love for books and storytelling.'),
        ('fa-solid fa-music', 'Music & Cultural Club', 'Celebrating creativity, rhythm and Nigerian culture.'),
    ],
    ('academics', 'levels'): [
        ('fa-solid fa-baby', 'Creche', 'Nurturing care and sensory development in a safe and loving environment for our youngest learners.'),
        ('fa-solid fa-shapes', 'Pre-Nursery', 'Early learning through play, exploration and discovery, building curiosity and social skills.'),
        ('fa-solid fa-puzzle-piece', 'Nursery', 'Building a strong foundation through play and discovery, introducing numeracy and literacy.'),
        ('fa-solid fa-book', 'Primary', 'Nurturing young minds for academic excellence across core and enrichment subjects.'),
        ('fa-solid fa-graduation-cap', 'Secondary', 'Preparing students for leadership and global impact through JSS1–3 and SSS1–3, in readiness for WAEC and NECO examinations.'),
    ],
    ('academics', 'calendar'): [
        ('fa-solid fa-calendar-days', 'Academic Calendar', 'Three terms per session — First, Second and Third Term — each with a mid-term break, examinations and a defined resumption date.'),
        ('fa-solid fa-person-chalkboard', 'Teaching Approach', 'Interactive, activity-based teaching combined with digital tools in the ICT-equipped classrooms.'),
        ('fa-solid fa-clipboard-check', 'Assessment & Examination', 'Continuous Assessment (CA) plus end-of-term examinations, with results issued via digital report cards.'),
    ],
}


class Command(BaseCommand):
    help = 'One-time seed of the site copy that used to be hardcoded in templates, into PageSection/ContentBlock.'

    def handle(self, *args, **options):
        section_count = 0
        for data in SECTIONS:
            _, created = PageSection.objects.get_or_create(key=data['key'], defaults=data)
            section_count += created

        block_count = 0
        for (page, section), cards in BLOCKS.items():
            for order, (icon, title, description) in enumerate(cards, start=1):
                _, created = ContentBlock.objects.get_or_create(
                    page=page, section=section, title=title,
                    defaults={'icon': icon, 'description': description, 'order': order},
                )
                block_count += created

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {section_count} new page section(s) and {block_count} new content block(s) '
            f'(already-existing rows left untouched).'
        ))
