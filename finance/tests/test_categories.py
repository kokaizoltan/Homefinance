"""Kategóriakezelési tesztek."""
from django.test import TestCase
from django.urls import reverse

from finance.models import Category

from .base import create_category, create_transaction, create_user


class CategoryCrudTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other_user = create_user(email="masik@example.com")
        self.category = create_category(self.user, name="Élelmiszer")
        self.other_category = create_category(self.other_user, name="Idegen")
        self.client.force_login(self.user)

    def test_list_only_contains_own_categories(self):
        response = self.client.get(reverse("finance:category_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Élelmiszer")
        self.assertNotContains(response, "Idegen")

    def test_create_category(self):
        response = self.client.post(
            reverse("finance:category_create"),
            {"name": "Közlekedés", "type": Category.TYPE_EXPENSE},
        )
        self.assertRedirects(response, reverse("finance:category_list"))
        self.assertTrue(
            Category.objects.filter(
                owner=self.user, name="Közlekedés", type=Category.TYPE_EXPENSE
            ).exists()
        )

    def test_duplicate_category_is_rejected(self):
        response = self.client.post(
            reverse("finance:category_create"),
            {"name": "élelmiszer", "type": Category.TYPE_EXPENSE},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Már létezik ilyen nevű kategória")
        self.assertEqual(Category.objects.filter(owner=self.user).count(), 1)
        self.assertEqual(Category.objects.get(owner=self.user).name, "Élelmiszer")

    def test_same_name_with_other_type_is_allowed(self):
        response = self.client.post(
            reverse("finance:category_create"),
            {"name": "Élelmiszer", "type": Category.TYPE_INCOME},
        )
        self.assertRedirects(response, reverse("finance:category_list"))
        self.assertEqual(
            Category.objects.filter(owner=self.user, name="Élelmiszer").count(), 2
        )

    def test_name_is_trimmed(self):
        self.client.post(
            reverse("finance:category_create"),
            {"name": "  Zöldség  ", "type": Category.TYPE_EXPENSE},
        )
        self.assertTrue(
            Category.objects.filter(owner=self.user, name="Zöldség").exists()
        )

    def test_update_own_category(self):
        response = self.client.post(
            reverse("finance:category_update", args=[self.category.pk]),
            {"name": "Élelmiszer és háztartás", "type": Category.TYPE_EXPENSE},
        )
        self.assertRedirects(response, reverse("finance:category_list"))
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, "Élelmiszer és háztartás")

    def test_cannot_change_type_of_used_category(self):
        create_transaction(self.user, category=self.category)
        response = self.client.post(
            reverse("finance:category_update", args=[self.category.pk]),
            {"name": self.category.name, "type": Category.TYPE_INCOME},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "típusa nem módosítható")
        self.category.refresh_from_db()
        self.assertEqual(self.category.type, Category.TYPE_EXPENSE)

    def test_cannot_update_other_users_category(self):
        response = self.client.get(
            reverse("finance:category_update", args=[self.other_category.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_unused_category(self):
        response = self.client.post(
            reverse("finance:category_delete", args=[self.category.pk])
        )
        self.assertRedirects(response, reverse("finance:category_list"))
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())

    def test_used_category_cannot_be_deleted(self):
        create_transaction(self.user, category=self.category)
        response = self.client.post(
            reverse("finance:category_delete", args=[self.category.pk]), follow=True
        )
        self.assertContains(response, "nem törölhető, mert használatban van")
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    def test_cannot_delete_other_users_category(self):
        response = self.client.post(
            reverse("finance:category_delete", args=[self.other_category.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=self.other_category.pk).exists())

    def test_delete_requires_post(self):
        response = self.client.get(
            reverse("finance:category_delete", args=[self.category.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())
