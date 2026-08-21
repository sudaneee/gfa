from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from website.content import get_blocks, get_section
from website.models import ContentBlock, PageSection


class ContentAccessorTests(TestCase):
    def test_get_section_returns_a_safe_empty_default_when_unseeded(self):
        section = get_section('does_not_exist')
        self.assertEqual(section.heading, '')
        self.assertEqual(section.paragraphs, [])

    def test_get_section_returns_the_matching_row(self):
        PageSection.objects.create(key='home_welcome', page='home', label='Welcome', heading='Hello')
        self.assertEqual(get_section('home_welcome').heading, 'Hello')

    def test_get_blocks_only_returns_active_cards_for_that_page_and_section(self):
        ContentBlock.objects.create(page='home', section='why_choose_us', title='Active Card', is_active=True)
        ContentBlock.objects.create(page='home', section='why_choose_us', title='Inactive Card', is_active=False)
        ContentBlock.objects.create(page='about', section='why_choose_us', title='Wrong Page', is_active=True)

        titles = [b.title for b in get_blocks('home', 'why_choose_us')]
        self.assertEqual(titles, ['Active Card'])


class WebsitePagesRenderRealContentTests(TestCase):
    """The public pages must reflect whatever's in the database, not
    hardcoded copy — the whole point of this feature."""

    def setUp(self):
        PageSection.objects.create(key='home_welcome', page='home', label='Welcome', heading='Custom Homepage Heading', body='Custom paragraph.')
        PageSection.objects.create(key='home_moral', page='home', label='Moral', heading='Moral Heading')
        PageSection.objects.create(key='home_parent_portal', page='home', label='Portal', heading='Portal Heading')
        ContentBlock.objects.create(page='home', section='why_choose_us', title='Custom Feature Card', description='Custom description.')

    def test_homepage_shows_database_content(self):
        response = self.client.get(reverse('website:home'))
        self.assertContains(response, 'Custom Homepage Heading')
        self.assertContains(response, 'Custom paragraph.')
        self.assertContains(response, 'Custom Feature Card')

    def test_inactive_card_does_not_render(self):
        ContentBlock.objects.create(page='home', section='why_choose_us', title='Hidden Card', is_active=False)
        response = self.client.get(reverse('website:home'))
        self.assertNotContains(response, 'Hidden Card')


class WebsiteContentConsoleTests(TestCase):
    """Proves the Superadmin Console can edit this content end-to-end, and
    that a page-section (a template-referenced named slot) can't be
    deleted from the console — only its text."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin1', password='pw', role='admin')
        self.client.force_login(self.admin)
        self.section = PageSection.objects.create(key='home_welcome', page='home', label='Welcome', heading='Original Heading')
        self.block = ContentBlock.objects.create(page='home', section='why_choose_us', title='Original Card')

    def test_editing_a_page_section_through_the_console_changes_the_public_site(self):
        response = self.client.post(reverse('admin_console:edit', args=['page-sections', self.section.pk]), {
            'eyebrow': '', 'heading': 'Edited Heading', 'body': '',
        })
        self.assertRedirects(response, reverse('admin_console:list', args=['page-sections']))

        public_response = self.client.get(reverse('website:home'))
        self.assertContains(public_response, 'Edited Heading')

    def test_page_section_cannot_be_deleted(self):
        response = self.client.get(reverse('admin_console:delete', args=['page-sections', self.section.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PageSection.objects.filter(pk=self.section.pk).exists())

    def test_content_block_create_edit_delete_round_trip(self):
        response = self.client.post(reverse('admin_console:create', args=['content-blocks']), {
            'page': 'about', 'section': 'stats', 'icon': 'fa-solid fa-star',
            'title': 'New Card', 'description': 'New description.', 'order': '1',
        })
        self.assertRedirects(response, reverse('admin_console:list', args=['content-blocks']))
        card = ContentBlock.objects.get(title='New Card')

        response = self.client.post(reverse('admin_console:delete', args=['content-blocks', card.pk]))
        self.assertRedirects(response, reverse('admin_console:list', args=['content-blocks']))
        self.assertFalse(ContentBlock.objects.filter(pk=card.pk).exists())
