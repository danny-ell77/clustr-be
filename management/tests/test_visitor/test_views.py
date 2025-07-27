
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import create_user, create_cluster, create_visitor, create_visitor_log
from core.common.models import Visitor, VisitorLog


class ManagementVisitorViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.visitor = create_visitor(self.cluster, self.admin_user)

    def test_list_visitors_authenticated_with_permission(self):
        """
        Ensure users with permission can list visitors.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_visitor_authenticated_with_permission(self):
        """
        Ensure users with permission can create a visitor.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-list")
        data = {
            "name": "New Visitor",
            "phone": "+1123456789",
            "estimated_arrival": "2025-12-31T10:00:00Z",
            "valid_date": "2025-12-31",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_check_in_visitor(self):
        """
        Ensure a visitor can be checked in.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-check-in", kwargs={"pk": self.visitor.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.visitor.refresh_from_db()
        self.assertEqual(self.visitor.status, Visitor.Status.CHECKED_IN)

    def test_check_out_visitor(self):
        """
        Ensure a visitor can be checked out.
        """
        self.visitor.status = Visitor.Status.CHECKED_IN
        self.visitor.save()
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-check-out", kwargs={"pk": self.visitor.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.visitor.refresh_from_db()
        self.assertEqual(self.visitor.status, Visitor.Status.CHECKED_OUT)

    def test_validate_access_code(self):
        """
        Ensure a visitor's access code can be validated.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-validate-access-code", kwargs={"pk": self.visitor.pk})
        data = {"access_code": self.visitor.access_code}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])

    def test_retrieve_visitor(self):
        """
        Ensure an admin can retrieve a visitor.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-detail", kwargs={"pk": self.visitor.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_visitor(self):
        """
        Ensure an admin can update a visitor.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-detail", kwargs={"pk": self.visitor.pk})
        data = {"name": "Updated Visitor Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.visitor.refresh_from_db()
        self.assertEqual(self.visitor.name, "Updated Visitor Name")

    def test_delete_visitor(self):
        """
        Ensure an admin can delete a visitor.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitor-detail", kwargs={"pk": self.visitor.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)



class ManagementVisitorLogViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.visitor = create_visitor(self.cluster, self.admin_user)
        self.visitor_log = create_visitor_log(self.visitor)

    def test_list_visitor_logs(self):
        """
        Ensure visitor logs can be listed.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitorlog-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_retrieve_visitor_log(self):
        """
        Ensure an admin can retrieve a visitor log.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitorlog-detail", kwargs={"pk": self.visitor_log.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_visitor_log(self):
        """
        Ensure an admin can delete a visitor log.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:visitorlog-detail", kwargs={"pk": self.visitor_log.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
