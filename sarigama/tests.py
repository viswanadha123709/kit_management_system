from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
import json
from . import models

class SarigamaAppTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = models.user.objects.create(
            user_name="John Doe",
            user_age=25,
            user_number=9876543210,
            user_adhar=123456789012
        )
        self.inst1 = models.instrument.objects.create(
            instrument_name="Keyboard Synth",
            brand="Roland",
            specifiations="61 keys, MIDI capable",
            working=True
        )
        self.inst2 = models.instrument.objects.create(
            instrument_name="Electric Guitar",
            brand="Fender",
            specifiations="Stratocaster with dual pickups",
            working=True
        )
        self.kit = models.kit.objects.create(
            cost=1500.00,
            items=[self.inst1.id, self.inst2.id]
        )

    def test_get_home_page(self):
        response = self.client.get('/home/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SARIGAMA")
        self.assertContains(response, "Keyboard Synth")
        self.assertContains(response, "John Doe")

    def test_get_root_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SARIGAMA")

    def test_register_user_post(self):
        response = self.client.post('/home/', {
            'action': 'register_user',
            'name': 'Jane Smith',
            'age': '28',
            'number': '9812345678',
            'adhar': '987654321012'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(models.user.objects.filter(user_name='Jane Smith').exists())

    def test_insert_instrument_post(self):
        response = self.client.post('/home/', {
            'action': 'insert_item',
            'name': 'Studio Monitor',
            'brand': 'Yamaha',
            'specifications': 'Active 8-inch bi-amplified'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(models.instrument.objects.filter(instrument_name='Studio Monitor').exists())

    def test_add_and_remove_kit_post(self):
        response = self.client.post('/home/', {
            'action': 'add_kit',
            'cost': '2500.00',
            'items': json.dumps([self.inst1.id])
        })
        self.assertEqual(response.status_code, 200)
        created_kit = models.kit.objects.filter(cost=2500.00).first()
        self.assertIsNotNone(created_kit)

        # Remove kit
        del_response = self.client.post('/home/', {
            'action': 'remove_kit',
            'id': str(created_kit.id)
        })
        self.assertEqual(del_response.status_code, 200)
        self.assertFalse(models.kit.objects.filter(id=created_kit.id).exists())

    def test_booking_and_conflict(self):
        start = timezone.now() + timedelta(days=1)
        end = start + timedelta(hours=2)

        # First booking succeeds
        resp1 = self.client.post('/home/', {
            'action': 'book_kit',
            'userid': str(self.user.id),
            'kit_id': str(self.kit.id),
            'start': start.isoformat(),
            'end': end.isoformat()
        })
        self.assertEqual(resp1.status_code, 200)
        self.assertContains(resp1, "booked successfully")

        # Conflicting booking fails
        resp2 = self.client.post('/home/', {
            'action': 'book_kit',
            'userid': str(self.user.id),
            'kit_id': str(self.kit.id),
            'start': start.isoformat(),
            'end': end.isoformat()
        })
        self.assertEqual(resp2.status_code, 200)
        self.assertContains(resp2, "not available")

    def test_inspection_and_faulty_toggle(self):
        # Mark faulty
        resp1 = self.client.post('/home/', {
            'action': 'mark_faulty',
            'kit_id': str(self.kit.id),
            'instrument_id': str(self.inst1.id)
        })
        self.assertEqual(resp1.status_code, 200)
        self.inst1.refresh_from_db()
        self.assertFalse(self.inst1.working)

        # Check kit reports faulty
        resp_check = self.client.post('/home/', {
            'action': 'check_kit',
            'kit_id': str(self.kit.id)
        })
        self.assertContains(resp_check, "FAULTY")

        # Mark working
        resp2 = self.client.post('/home/', {
            'action': 'mark_working',
            'kit_id': str(self.kit.id),
            'instrument_id': str(self.inst1.id)
        })
        self.assertEqual(resp2.status_code, 200)
        self.inst1.refresh_from_db()
        self.assertTrue(self.inst1.working)
