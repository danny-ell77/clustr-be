"""
Tests for member emergency contact views.
"""
import uuid
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse

from core.common.models.emergency import EmergencyContact
from .utils import create_cluster, create_user, create_emergency_contact, authenticate_user


class EmergencyContactListViewTests(APITestCase):
    """
    Test cases for EmergencyContactListView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="emergency@example.com", cluster=self.cluster)

    def test_list_unauthenticated(self):
        """
        Unauthenticated users should not be able to list emergency contacts.
        """
        url = reverse("members:emergency_contacts")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_empty(self):
        """
        User with no emergency contacts should get an empty list.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contacts")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_list_with_contacts(self):
        """
        User should see their own emergency contacts.
        """
        create_emergency_contact(self.member, name="Contact 1")
        create_emergency_contact(self.member, name="Contact 2", phone="+2348000000002")
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contacts")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_does_not_show_other_users_contacts(self):
        """
        User should not see emergency contacts of other users.
        """
        other_user = create_user(email="other@example.com", cluster=self.cluster)
        create_emergency_contact(other_user, name="Other's Contact")
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contacts")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_contact(self):
        """
        User should be able to create an emergency contact.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contacts")
        data = {
            "name": "New Contact",
            "phone_number": "+2348000000050",
            "contact_type": "FRIEND",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(EmergencyContact.objects.filter(name="New Contact", user=self.member).exists())

    def test_create_contact_missing_required_fields(self):
        """
        Creating a contact without required fields should fail.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contacts")
        data = {"name": "Incomplete Contact"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmergencyContactDetailViewTests(APITestCase):
    """
    Test cases for EmergencyContactDetailView.
    """

    def setUp(self):
        self.cluster, self.admin = create_cluster()
        self.member = create_user(email="emergencydetail@example.com", cluster=self.cluster)
        self.contact = create_emergency_contact(self.member)

    def test_retrieve_unauthenticated(self):
        """
        Unauthenticated users should not be able to retrieve a contact.
        """
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(self.contact.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_own_contact(self):
        """
        User should be able to retrieve their own emergency contact.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(self.contact.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.contact.name)

    def test_retrieve_other_users_contact(self):
        """
        User should not be able to retrieve another user's contact.
        """
        other_user = create_user(email="otheruser@example.com", cluster=self.cluster)
        other_contact = create_emergency_contact(other_user, name="Other Contact")
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(other_contact.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_contact(self):
        """
        Retrieving a non-existent contact should return 404.
        """
        authenticate_user(self.client, self.member)
        fake_id = uuid.uuid4()
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(fake_id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_contact(self):
        """
        User should be able to update their emergency contact.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(self.contact.id)})
        data = {"name": "Updated Contact Name"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.name, "Updated Contact Name")

    def test_delete_contact(self):
        """
        User should be able to delete their emergency contact.
        """
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(self.contact.id)})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EmergencyContact.objects.filter(id=self.contact.id).exists())

    def test_delete_other_users_contact_fails(self):
        """
        User should not be able to delete another user's contact.
        """
        other_user = create_user(email="otheruserdel@example.com", cluster=self.cluster)
        other_contact = create_emergency_contact(other_user, name="Del Contact")
        authenticate_user(self.client, self.member)
        url = reverse("members:emergency_contact_detail", kwargs={"pk": str(other_contact.id)})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(EmergencyContact.objects.filter(id=other_contact.id).exists())
