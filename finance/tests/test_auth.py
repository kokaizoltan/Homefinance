"""Hitelesítési tesztek: regisztráció, bejelentkezés, kijelentkezés, jogosultság."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .base import create_user

User = get_user_model()


class RegistrationTests(TestCase):
    def test_register_page_is_available(self):
        response = self.client.get(reverse("finance:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fiók létrehozása")

    def test_successful_registration_creates_user(self):
        response = self.client.post(
            reverse("finance:register"),
            {
                "email": "Uj.Felhasznalo@Example.COM",
                "last_name": "Nagy",
                "first_name": "Béla",
                "password1": "NagyonTitkos123!",
                "password2": "NagyonTitkos123!",
            },
        )
        self.assertRedirects(response, reverse("finance:login"))
        user = User.objects.get(email="uj.felhasznalo@example.com")
        self.assertTrue(user.check_password("NagyonTitkos123!"))
        self.assertEqual(user.first_name, "Béla")

    def test_duplicate_email_is_rejected_case_insensitively(self):
        create_user(email="letezo@example.com")
        response = self.client.post(
            reverse("finance:register"),
            {
                "email": "LETEZO@example.com",
                "password1": "NagyonTitkos123!",
                "password2": "NagyonTitkos123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "már létezik felhasználó")
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse("finance:register"),
            {
                "email": "gyenge@example.com",
                "password1": "123",
                "password2": "123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="gyenge@example.com").exists())

    def test_authenticated_user_is_redirected_from_registration(self):
        user = create_user()
        self.client.force_login(user)
        response = self.client.get(reverse("finance:register"))
        self.assertRedirects(response, reverse("finance:dashboard"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = create_user(email="bejelentkezo@example.com", password="Titok12345!")

    def test_login_with_email_succeeds(self):
        response = self.client.post(
            reverse("finance:login"),
            {"username": "bejelentkezo@example.com", "password": "Titok12345!"},
        )
        self.assertRedirects(response, reverse("finance:dashboard"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse("finance:login"),
            {"username": "bejelentkezo@example.com", "password": "rossz-jelszo"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "helyes e-mail")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_email_is_case_insensitive(self):
        response = self.client.post(
            reverse("finance:login"),
            {"username": "BEJELENTKEZO@Example.COM", "password": "Titok12345!"},
        )
        self.assertRedirects(response, reverse("finance:dashboard"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("finance:login"), response.url)

    def test_logout_requires_post_and_logs_out(self):
        self.client.force_login(self.user)
        get_response = self.client.get(reverse("finance:logout"))
        self.assertEqual(get_response.status_code, 405)

        response = self.client.post(reverse("finance:logout"))
        self.assertRedirects(response, reverse("finance:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
