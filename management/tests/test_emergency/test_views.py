from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import (
    create_user,
    create_cluster,
    create_emergency_contact,
    create_sos_alert,
    create_emergency_response,
)
from core.common.models import EmergencyContactType, EmergencyType, EmergencyStatus


class EmergencyContactManagementViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.emergency_contact = create_emergency_contact(self.cluster, self.user)

    def test_list_emergency_contacts_unauthenticated(self):
        """
        Ensure unauthenticated users cannot list emergency contacts.
        """
        url = reverse("management:emergencycontact-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_emergency_contacts_authenticated_no_permission(self):
        """
        Ensure users without permission cannot list emergency contacts.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:emergencycontact-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_emergency_contacts_authenticated_with_permission(self):
        """
        Ensure users with permission can list emergency contacts.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_emergency_contact_unauthenticated(self):
        """
        Ensure unauthenticated users cannot create emergency contacts.
        """
        url = reverse("management:emergencycontact-list")
        data = {
            "name": "New Contact",
            "phone_number": "+1987654321",
            "contact_type": EmergencyContactType.PERSONAL,
            "emergency_types": [EmergencyType.HEALTH],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_emergency_contact_authenticated_no_permission(self):
        """
        Ensure users without permission cannot create emergency contacts.
        """
        self.client.force_authenticate(user=self.user)
        url = reverse("management:emergencycontact-list")
        data = {
            "name": "New Contact",
            "phone_number": "+1987654321",
            "contact_type": EmergencyContactType.PERSONAL,
            "emergency_types": [EmergencyType.HEALTH],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_emergency_contact_authenticated_with_permission(self):
        """
        Ensure users with permission can create emergency contacts.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-list")
        data = {
            "name": "New Contact",
            "phone_number": "+1987654321",
            "contact_type": EmergencyContactType.ESTATE_WIDE,
            "emergency_types": [EmergencyType.SECURITY],
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_emergency_contact(self):
        """
        Ensure an admin can retrieve an emergency contact.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-detail", kwargs={"pk": self.emergency_contact.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_emergency_contact(self):
        """
        Ensure an admin can update an emergency contact.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-detail", kwargs={"pk": self.emergency_contact.pk})
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.emergency_contact.refresh_from_db()
        self.assertEqual(self.emergency_contact.name, "Updated Name")

    def test_delete_emergency_contact(self):
        """
        Ensure an admin can delete an emergency contact.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-detail", kwargs={"pk": self.emergency_contact.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_estate_wide_contacts(self):
        """
        Ensure estate-wide contacts can be retrieved.
        """
        create_emergency_contact(self.cluster, contact_type=EmergencyContactType.ESTATE_WIDE)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-estate-wide")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_contacts_by_type(self):
        """
        Ensure contacts can be filtered by emergency type.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-by-type")
        response = self.client.get(url, {"emergency_type": EmergencyType.HEALTH})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_emergency_types(self):
        """
        Ensure the list of emergency types is returned.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-emergency-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_get_contact_types(self):
        """
        Ensure the list of contact types is returned.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencycontact-contact-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)


class SOSAlertManagementViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.sos_alert = create_sos_alert(self.cluster, self.user)

    def test_list_sos_alerts_authenticated_with_permission(self):
        """
        Ensure users with permission can list SOS alerts.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_acknowledge_alert(self):
        """
        Ensure an admin can acknowledge an SOS alert.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-acknowledge", kwargs={"pk": self.sos_alert.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sos_alert.refresh_from_db()
        self.assertEqual(self.sos_alert.status, EmergencyStatus.ACKNOWLEDGED)

    def test_start_response(self):
        """
        Ensure an admin can start a response to an SOS alert.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-start-response", kwargs={"pk": self.sos_alert.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sos_alert.refresh_from_db()
        self.assertEqual(self.sos_alert.status, EmergencyStatus.RESPONDING)

    def test_resolve_alert(self):
        """
        Ensure an admin can resolve an SOS alert.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-resolve", kwargs={"pk": self.sos_alert.pk})
        response = self.client.post(url, {"notes": "Resolved"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sos_alert.refresh_from_db()
        self.assertEqual(self.sos_alert.status, EmergencyStatus.RESOLVED)

    def test_cancel_alert(self):
        """
        Ensure an admin can cancel an SOS alert.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-cancel", kwargs={"pk": self.sos_alert.pk})
        response = self.client.post(url, {"reason": "Cancelled"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sos_alert.refresh_from_db()
        self.assertEqual(self.sos_alert.status, EmergencyStatus.CANCELLED)

    def test_get_active_alerts(self):
        """
        Ensure active alerts can be retrieved.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-active")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_statistics(self):
        """
        Ensure emergency statistics can be retrieved.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_alerts", response.data)

    def test_get_emergency_types(self):
        """
        Ensure the list of emergency types is returned.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-emergency-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_get_status_choices(self):
        """
        Ensure the list of status choices is returned.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-status-choices")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response..data), 0)

    def test_get_responses(self):
        """
        Ensure responses for an alert can be retrieved.
        """
        create_emergency_response(self.sos_alert, self.admin_user)
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-responses", kwargs={"pk": self.sos_alert.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_generate_report(self):
        """
        Ensure an emergency report can be generated.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-generate-report")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_incident_report(self):
        """
        Ensure an incident report for a specific alert can be generated.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:sosalert-incident-report", kwargs={"pk": self.sos_alert.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EmergencyResponseManagementViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.sos_alert = create_sos_alert(self.cluster, self.user)
        self.emergency_response = create_emergency_response(self.sos_alert, self.admin_user)

    def test_list_emergency_responses_authenticated_with_permission(self):
        """
        Ensure users with permission can list emergency responses.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencyresponse-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_emergency_response(self):
        """
        Ensure an admin can create an emergency response.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:emergencyresponse-list")
        data = {"alert": self.sos_alert.pk, "response_type": "dispatched"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_emergency_response(self):
        """
        Ensure an admin can retrieve an emergency response.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:emergencyresponse-detail",
            kwargs={"pk": self.emergency_response.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_emergency_response(self):
        """
        Ensure an admin can update an emergency response.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:emergencyresponse-detail",
            kwargs={"pk": self.emergency_response.pk},
        )
        data = {"notes": "Updated notes"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.emergency_response.refresh_from_db()
        self.assertEqual(self.emergency_response.notes, "Updated notes")

    def test_delete_emergency_response(self):
        """
        Ensure an admin can delete an emergency response.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:emergencyresponse-detail",
            kwargs={"pk": self.emergency_response.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)