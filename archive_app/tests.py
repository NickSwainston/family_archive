import shutil
import tempfile
from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Event, MediaFile, UploadedBy, FamilyMember

# 1x1 GIF so uploads are real image bytes
PIXEL = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04'
         b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')

TMP_MEDIA = tempfile.mkdtemp()


def upload(name='photo.gif'):
    return SimpleUploadedFile(name, PIXEL, content_type='image/gif')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class EventModelTests(TestCase):
    def test_end_before_start_is_invalid(self):
        event = Event(title='Trip', start_date=date(2024, 1, 5), end_date=date(2024, 1, 1))
        with self.assertRaises(ValidationError):
            event.full_clean()

    def test_date_range_display(self):
        cases = [
            (date(2024, 1, 3), None, '3 Jan 2024'),
            (date(2024, 1, 3), date(2024, 1, 3), '3 Jan 2024'),
            (date(2024, 1, 3), date(2024, 1, 9), '3 – 9 Jan 2024'),
            (date(2024, 1, 30), date(2024, 2, 2), '30 Jan – 2 Feb 2024'),
            (date(2023, 12, 28), date(2024, 1, 2), '28 Dec 2023 – 2 Jan 2024'),
        ]
        for start, end, expected in cases:
            self.assertEqual(Event(title='x', start_date=start, end_date=end).date_range_display(), expected)


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class EventViewTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.alice = User.objects.create_user('alice', password='pw')
        self.bob = User.objects.create_user('bob', password='pw')

    def test_timeline_requires_login(self):
        resp = self.client.get(reverse('timeline'))
        self.assertEqual(resp.status_code, 302)

    def test_timeline_groups_events_by_year(self):
        Event.objects.create(title='Old reunion', start_date=date(2019, 6, 1))
        Event.objects.create(title='Beach trip', start_date=date(2024, 1, 3), end_date=date(2024, 1, 9))
        self.client.force_login(self.alice)
        resp = self.client.get(reverse('timeline'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([year for year, _ in resp.context['years']], [2024, 2019])
        self.assertContains(resp, 'Beach trip')
        self.assertContains(resp, '3 – 9 Jan 2024')

    def test_create_event_with_photos(self):
        self.client.force_login(self.alice)
        resp = self.client.post(reverse('event_create'), {
            'title': 'Christmas', 'place': 'Perth', 'start_date': '2024-12-25', 'end_date': '',
            'description': '', 'images': [upload('a.gif'), upload('b.gif')],
        })
        event = Event.objects.get(title='Christmas')
        self.assertRedirects(resp, reverse('event_detail', args=[event.id]))
        self.assertEqual(event.created_by, self.alice)
        self.assertEqual(event.images.count(), 2)

    def test_detail_and_form_pages_render(self):
        event = Event.objects.create(title='Wedding', place='Fremantle', start_date=date(2022, 3, 1), created_by=self.alice)
        event.images.add(MediaFile.objects.create(
            uploaded_by=UploadedBy.objects.create(user=self.alice), media_path=upload()))
        self.client.force_login(self.alice)
        detail = self.client.get(reverse('event_detail', args=[event.id]))
        self.assertContains(detail, 'Fremantle')
        self.assertContains(detail, 'href="%s"' % reverse('event_edit', args=[event.id]))
        self.assertEqual(self.client.get(reverse('event_create')).status_code, 200)
        self.assertContains(self.client.get(reverse('event_edit', args=[event.id])), 'Save changes')

    def test_other_users_can_add_photos(self):
        event = Event.objects.create(title='Wedding', start_date=date(2022, 3, 1), created_by=self.alice)
        self.client.force_login(self.bob)
        self.client.post(reverse('event_detail', args=[event.id]), {'images': [upload()]})
        self.assertEqual(event.images.get().uploaded_by.user, self.bob)

    def test_only_creator_or_superuser_can_edit(self):
        event = Event.objects.create(title='Wedding', start_date=date(2022, 3, 1), created_by=self.alice)
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse('event_edit', args=[event.id])).status_code, 403)
        self.client.force_login(self.alice)
        resp = self.client.post(reverse('event_edit', args=[event.id]), {
            'title': 'Our wedding', 'place': '', 'start_date': '2022-03-01', 'end_date': '', 'description': '',
        })
        self.assertEqual(resp.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, 'Our wedding')


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class PerFileUploadTests(TestCase):
    """The browser uploads one file per request to stay under Cloudflare's 100 MB limit."""
    AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    def setUp(self):
        self.user = User.objects.create_user('alice')
        self.client.force_login(self.user)

    def test_gallery_upload_returns_ids_and_tag_page_accepts_them(self):
        ids = [self.client.post('/gallery/', {'images': [upload()]}, **self.AJAX).json()['ids'][0] for _ in range(2)]
        resp = self.client.get(reverse('tag_images'), {'ids': ','.join(map(str, ids))})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['image_forms']), 2)

    def test_tag_page_ignores_other_users_uploads(self):
        other = User.objects.create_user('bob')
        media = MediaFile.objects.create(uploaded_by=UploadedBy.objects.create(user=other), media_path=upload())
        resp = self.client.get(reverse('tag_images'), {'ids': str(media.id)})
        self.assertRedirects(resp, '/gallery/', fetch_redirect_response=False)

    def test_create_event_then_upload_files_separately(self):
        resp = self.client.post(reverse('event_create'), {
            'title': 'Picnic', 'place': '', 'start_date': '2025-02-01', 'end_date': '', 'description': '',
        }, **self.AJAX)
        upload_url = resp.json()['upload_url']
        for name in ('a.gif', 'b.gif', 'c.gif'):
            self.assertEqual(len(self.client.post(upload_url, {'images': [upload(name)]}, **self.AJAX).json()['ids']), 1)
        self.assertEqual(Event.objects.get(title='Picnic').images.count(), 3)

    def test_create_event_ajax_validation_errors(self):
        resp = self.client.post(reverse('event_create'), {
            'title': 'Bad', 'start_date': '2025-02-05', 'end_date': '2025-02-01',
        }, **self.AJAX)
        self.assertEqual(resp.status_code, 400)
        self.assertIn('end_date', resp.json()['errors'])


@override_settings(MEDIA_ROOT=TMP_MEDIA, DEBUG=False)
class MediaServingTests(TestCase):
    def test_uploaded_media_served_when_debug_off(self):
        user = User.objects.create_user('alice')
        media = MediaFile.objects.create(uploaded_by=UploadedBy.objects.create(user=user), media_path=upload())
        resp = self.client.get(media.media_path.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b''.join(resp.streaming_content), PIXEL)


class FamilyTreeTests(TestCase):
    def setUp(self):
        self.dad = FamilyMember.objects.create(full_name="Dad O'Brien", gender='m', email='dad@example.com')
        self.mum = FamilyMember.objects.create(full_name='Mum', gender='f', partner=self.dad)
        self.kid = FamilyMember.objects.create(full_name='Kid', gender='f', father=self.dad, mother=self.mum)

    def people(self, response):
        return {p['id']: p for p in response.context['tree_data']}

    def test_relationships_are_symmetric(self):
        people = self.people(self.client.get('/family_tree/'))
        dad, mum, kid = (people[str(m.id)] for m in (self.dad, self.mum, self.kid))
        self.assertEqual(dad['rels']['spouses'], [str(self.mum.id)])
        self.assertEqual(mum['rels']['spouses'], [str(self.dad.id)])
        self.assertEqual(kid['rels']['parents'], [str(self.dad.id), str(self.mum.id)])
        self.assertEqual(dad['rels']['children'], [str(self.kid.id)])
        self.assertEqual(dad['data']['gender'], 'M')

    def test_contact_details_only_for_logged_in_users(self):
        dad_id = str(self.dad.id)
        self.assertNotIn('email', self.people(self.client.get('/family_tree/'))[dad_id]['data'])
        self.client.force_login(User.objects.create_user('member'))
        self.assertEqual(self.people(self.client.get('/family_tree/'))[dad_id]['data']['email'], 'dad@example.com')
