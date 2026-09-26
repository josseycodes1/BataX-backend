from datetime import timedelta
from unittest.mock import patch
from django.core import mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from accounts.models import User, EmailChallenge
from listings.models import Category, ItemListing, ItemMedia
from wishlist.models import WantedItem
from exchanges.models import ExchangeProposal, Exchange
from verification.models import PossessionVerification


class BataxAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        self.a = User.objects.create_user('alice@example.com', 'Strong!Pass8372', first_name='Alice',
            is_verified=True, is_phone_verified=True, is_identity_verified=True)
        self.b = User.objects.create_user('bob@example.com', 'Strong!Pass8372', first_name='Bob',
            is_verified=True, is_phone_verified=True, is_identity_verified=True)
        self.c = User.objects.create_user('third@example.com', 'Strong!Pass8372', is_verified=True)
        self.admin = User.objects.create_superuser('admin@example.com', 'Strong!Pass8372')
        self.category = Category.objects.create(name='Electronics', slug='electronics')
        self.x = self.item(self.a, 'PlayStation 5')
        self.y = self.item(self.b, 'iPhone 13')
        self.client.force_authenticate(self.a)

    def item(self, owner, title):
        return ItemListing.objects.create(owner=owner, title=title, category=self.category,
            description='An item with a detailed description.', condition='good', city='Lagos', state='Lagos',
            status='active', open_to_offers=True, possession_verified=True)

    def proposal(self):
        response = self.client.post('/api/proposals/', {'offered_item': str(self.x.pk), 'requested_item': str(self.y.pk)}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def exchange(self):
        proposal = self.proposal()
        self.client.force_authenticate(self.b)
        response = self.client.post(f'/api/proposals/{proposal}/accept/')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data['id']

    def test_registration_email_verification_and_login(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/accounts/register/', {'email': 'NEW@Example.COM', 'password': 'Good!Password937',
            'first_name': 'New', 'last_name': 'Trader', 'accept_terms': True, 'role': 'super_admin'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email='new@example.com')
        self.assertEqual(user.role, 'user')
        self.assertFalse(user.is_staff)
        self.assertEqual(len(mail.outbox), 1)
        credentials = {'email': 'NEW@EXAMPLE.COM', 'password': 'Good!Password937'}
        self.assertEqual(self.client.post('/api/accounts/login/', credentials).status_code, 400)
        challenge = EmailChallenge.objects.get(user=user)
        self.assertEqual(self.client.get(f'/api/accounts/verify-email/{challenge.token}/').status_code, 200)
        response = self.client.post('/api/accounts/login/', credentials)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(self.client.get(f'/api/accounts/verify-email/{challenge.token}/').status_code, 404)

    def test_case_insensitive_email_database_constraint(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user('ALICE@example.com', 'password')

    def test_profile_cannot_change_role_or_verification(self):
        response = self.client.patch('/api/accounts/profile/', {'first_name': 'Changed', 'role': 'super_admin',
            'is_identity_verified': False, 'email': 'hijack@example.com'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.a.refresh_from_db()
        self.assertEqual(self.a.role, 'user')
        self.assertEqual(self.a.email, 'alice@example.com')
        self.assertTrue(self.a.is_identity_verified)

    def test_public_profile_does_not_leak_private_fields(self):
        self.client.force_authenticate(None)
        response = self.client.get(f'/api/accounts/sellers/{self.a.public_id}/')
        self.assertEqual(response.status_code, 200)
        for field in ['email', 'phone_number', 'last_name', 'role']:
            self.assertNotIn(field, response.data)

    def test_phone_change_resets_verification(self):
        self.client.patch('/api/accounts/profile/', {'phone_number': '+2348012345678'})
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_phone_verified)

    def test_unverified_user_cannot_list(self):
        self.client.force_authenticate(self.c)
        response = self.client.post('/api/listings/', {'title': 'Laptop', 'category': str(self.category.pk),
            'description': 'Test', 'condition': 'good', 'state': 'Lagos', 'city': 'Lagos'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_non_owner_cannot_edit_listing(self):
        response = self.client.patch(f'/api/listings/{self.y.pk}/', {'title': 'Stolen'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_proposal_acceptance_and_dual_confirmation(self):
        exchange = self.exchange()
        self.x.refresh_from_db()
        self.assertEqual(self.x.status, 'in_exchange')
        self.assertEqual(self.client.post(f'/api/exchanges/{exchange}/confirm/').data['status'], 'agreed')
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.post(f'/api/exchanges/{exchange}/confirm/').data['status'], 'completed')
        self.y.refresh_from_db()
        self.assertEqual(self.y.status, 'exchanged')

    def test_acceptance_cancels_conflicting_offers(self):
        z = self.item(self.b, 'Laptop')
        conflict = ExchangeProposal.objects.create(sender=self.a, recipient=self.b, offered_item=self.x, requested_item=z)
        self.exchange()
        conflict.refresh_from_db()
        self.assertEqual(conflict.status, 'cancelled')
        self.assertEqual(self.client.post(f'/api/proposals/{conflict.pk}/accept/').status_code, 400)

    def test_only_recipient_can_accept(self):
        proposal = self.proposal()
        self.assertEqual(self.client.post(f'/api/proposals/{proposal}/accept/').status_code, 403)

    def test_exchange_and_messages_are_private(self):
        proposal = self.proposal()
        self.client.force_authenticate(self.c)
        self.assertEqual(self.client.get(f'/api/proposals/{proposal}/').status_code, 404)
        self.assertEqual(self.client.post('/api/messages/', {'proposal': proposal, 'body': 'Intruder'}).status_code, 403)

    def test_block_prevents_proposal(self):
        self.client.post('/api/accounts/blocks/', {'blocked_user': str(self.b.pk)})
        response = self.client.post('/api/proposals/', {'offered_item': str(self.x.pk), 'requested_item': str(self.y.pk)})
        self.assertEqual(response.status_code, 403)

    def test_matching_reciprocal(self):
        WantedItem.objects.create(user=self.a, listing=self.x, title='iPhone 13')
        WantedItem.objects.create(user=self.b, listing=self.y, title='PlayStation 5')
        response = self.client.get('/api/matches/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['results'][0]['type'], 'exact_reciprocal')

    def test_reviews_require_completion_and_are_unique(self):
        exchange = self.exchange()
        response = self.client.post('/api/reviews/', {'exchange': exchange, 'rating': 5})
        self.assertEqual(response.status_code, 400)
        self.client.post(f'/api/exchanges/{exchange}/confirm/')
        self.client.force_authenticate(self.a)
        self.client.post(f'/api/exchanges/{exchange}/confirm/')
        response = self.client.post('/api/reviews/', {'exchange': exchange, 'rating': 5})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.post('/api/reviews/', {'exchange': exchange, 'rating': 5}).status_code, 400)

    def test_dispute_freezes_confirmation_and_staff_resolves(self):
        exchange = self.exchange()
        response = self.client.post('/api/disputes/', {'exchange': exchange, 'reason': 'Damaged', 'description': 'Broken screen'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.client.post(f'/api/exchanges/{exchange}/confirm/').status_code, 400)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/admin/disputes/{response.data['id']}/resolve/", {'resolution': 'Items returned', 'outcome': 'cancelled'})
        self.assertEqual(response.status_code, 200, response.data)
        self.x.refresh_from_db()
        self.assertEqual(self.x.status, 'paused')

    def test_staff_routes_and_role_creation(self):
        self.assertEqual(self.client.get('/api/admin/users/').status_code, 403)
        self.client.force_authenticate(self.admin)
        response = self.client.post('/api/admin/users/create-account/', {'email': 'mod@example.com',
            'password': 'Strong!ModPass721', 'first_name': 'Mod', 'last_name': 'User', 'role': 'moderator'})
        self.assertEqual(response.status_code, 201, response.data)
        mod = User.objects.get(email='mod@example.com')
        self.assertFalse(mod.is_superuser)
        self.client.force_authenticate(mod)
        self.assertEqual(self.client.get('/api/admin/users/').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/listings/').status_code, 200)

    def test_identity_request_does_not_self_verify(self):
        self.a.is_identity_verified = False
        self.a.save()
        response = self.client.post('/api/accounts/verify-nin/', {'provider': 'manual-provider', 'reference': 'provider-ref-123'})
        self.assertEqual(response.status_code, 201, response.data)
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_identity_verified)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/admin/identity/{response.data['id']}/review/", {'decision': 'approve', 'reason': 'Provider checked'})
        self.assertEqual(response.status_code, 200, response.data)
        self.a.refresh_from_db()
        self.assertTrue(self.a.is_identity_verified)

    def test_expired_proposal_cannot_be_accepted(self):
        proposal = self.proposal()
        ExchangeProposal.objects.filter(pk=proposal).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.client.force_authenticate(self.b)
        self.assertEqual(self.client.post(f'/api/proposals/{proposal}/accept/').status_code, 400)

    def test_password_change_revokes_access_and_refresh(self):
        self.client.force_authenticate(None)
        tokens = self.client.post('/api/accounts/login/', {'email': self.a.email, 'password': 'Strong!Pass8372'}).data
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens['access'])
        response = self.client.post('/api/accounts/password-change/', {'old_password': 'Strong!Pass8372', 'new_password': 'Different!Pass629'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get('/api/accounts/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(self.client.post('/api/accounts/token/refresh/', {'refresh': tokens['refresh']}).status_code, 401)

    def test_otp_attempts_persist(self):
        from accounts.services import send_verification
        send_verification(self.c)
        self.client.force_authenticate(None)
        for _ in range(5):
            self.client.post('/api/accounts/verify-otp/', {'email': self.c.email, 'otp': 'wrong'})
        # Invalid syntax is rejected without consuming an attempt.
        self.assertEqual(EmailChallenge.objects.get(user=self.c).attempts, 0)
        for _ in range(5):
            self.client.post('/api/accounts/verify-otp/', {'email': self.c.email, 'otp': '123456'})
        self.assertEqual(EmailChallenge.objects.get(user=self.c).attempts, 5)

    def test_listing_publication_workflow(self):
        self.x.status = 'draft'
        self.x.possession_verified = False
        self.x.save()
        self.assertEqual(self.client.post(f'/api/listings/{self.x.pk}/submit/').status_code, 400)
        for i in range(2):
            ItemMedia.objects.create(listing=self.x, url=f'https://res.cloudinary.com/demo/{i}.jpg', public_id=str(i))
        PossessionVerification.objects.create(listing=self.x, code='BX-123', expires_at=timezone.now(),
            image_public_id='proof', status='submitted')
        check = self.x.possession
        self.client.force_authenticate(self.admin)
        with patch('moderation.views.private_image_url', return_value='https://signed.example/image'):
            response = self.client.post(f'/api/admin/possession/{check.pk}/review/', {'decision': 'approve', 'reason': 'Evidence checked'})
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.post(f'/api/listings/{self.x.pk}/submit/').status_code, 200)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/admin/listings/{self.x.pk}/review/', {'decision': 'approve', 'reason': 'Listing checked'})
        self.assertEqual(response.status_code, 200, response.data)
        self.x.refresh_from_db()
        self.assertEqual(self.x.status, 'active')

    def test_edit_invalidates_old_possession_evidence(self):
        check = PossessionVerification.objects.create(listing=self.x, code='BX-OLD',
            expires_at=timezone.now(), image_public_id='old-proof', status='submitted')
        self.client.patch(f'/api/listings/{self.x.pk}/', {'title': 'Different item'})
        check.refresh_from_db()
        self.assertEqual(check.status, 'rejected')
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'/api/admin/possession/{check.pk}/review/', {'decision': 'approve', 'reason': 'Old photo'})
        self.assertEqual(response.status_code, 400)

    def test_notification_is_private(self):
        self.proposal()
        self.assertEqual(self.client.get('/api/notifications/').data['count'], 0)
        self.client.force_authenticate(self.b)
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.data['count'], 1)
        notification = response.data['results'][0]['id']
        self.client.force_authenticate(self.a)
        self.assertEqual(self.client.post(f'/api/notifications/{notification}/read/').status_code, 404)

    def test_google_exchange_is_single_use(self):
        cache.set('google:exchange:test-code', {'email': 'google@example.com', 'first_name': 'Google', 'last_name': 'User'}, 120)
        self.client.force_authenticate(None)
        response = self.client.post('/api/accounts/auth/google/exchange/', {'code': 'test-code', 'accept_terms': True}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(User.objects.get(email='google@example.com').is_verified)
        self.assertEqual(self.client.post('/api/accounts/auth/google/exchange/', {'code': 'test-code'}).status_code, 400)

    def test_google_callback_rejects_wrong_state(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/accounts/auth/google/callback/?state=wrong&code=wrong')
        self.assertEqual(response.status_code, 400)

    def test_image_upload_uses_cloudinary(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buffer = io.BytesIO()
        Image.new('RGB', (8, 8), 'blue').save(buffer, format='PNG')
        image = SimpleUploadedFile('avatar.png', buffer.getvalue(), content_type='image/png')
        with patch('core.media.cloudinary.uploader.upload', return_value={
            'secure_url': 'https://res.cloudinary.com/demo/avatar.png', 'public_id': 'batax/avatars/avatar'}) as upload:
            response = self.client.patch('/api/accounts/profile/', {'profile_image': image}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        upload.assert_called_once()
        self.assertEqual(response.data['profile_image'], 'https://res.cloudinary.com/demo/avatar.png')

    def test_counter_offer_reverses_participants(self):
        proposal = self.proposal()
        self.client.force_authenticate(self.b)
        response = self.client.post(f'/api/proposals/{proposal}/counter/', {
            'offered_item': str(self.y.pk), 'requested_item': str(self.x.pk), 'message': 'Counter offer'})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(str(response.data['sender']), str(self.b.pk))
        self.assertEqual(ExchangeProposal.objects.get(pk=proposal).status, 'countered')
