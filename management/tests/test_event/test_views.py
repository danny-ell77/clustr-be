
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .utils import create_user, create_cluster, create_event, create_event_guest
from core.common.models import Event


class ManagementEventViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.event = create_event(self.cluster, self.admin_user)

    def test_list_events_authenticated_with_permission(self):
        """
        Ensure users with permission can list events.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_event_authenticated_with_permission(self):
        """
        Ensure users with permission can create an event.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-list")
        data = {
            "title": "New Event",
            "event_date": "2025-12-31",
            "event_time": "19:00",
            "location": "New Location",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_guests_to_event(self):
        """
        Ensure guests can be added to an event.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-add-guests", kwargs={"pk": self.event.pk})
        data = {"guests": [{"name": "Guest 1"}, {"name": "Guest 2"}]}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.event.guests.count(), 2)

    def test_publish_event(self):
        """
        Ensure an event can be published.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-publish", kwargs={"pk": self.event.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.PUBLISHED)

    def test_cancel_event(self):
        """
        Ensure an event can be cancelled.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-cancel", kwargs={"pk": self.event.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.Status.CANCELLED)

    def test_retrieve_event(self):
        """
        Ensure an admin can retrieve an event.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-detail", kwargs={"pk": self.event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_event(self):
        """
        Ensure an admin can update an event.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-detail", kwargs={"pk": self.event.pk})
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "Updated Title")

    def test_delete_event(self):
        """
        Ensure an admin can delete an event.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:event-detail", kwargs={"pk": self.event.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ManagementEventGuestViewSetTests(APITestCase):
    def setUp(self):
        self.cluster = create_cluster()
        self.user = create_user()
        self.admin_user = create_user(
            email="admin@example.com", name="Admin User", is_cluster_admin=True
        )
        self.user.clusters.add(self.cluster)
        self.admin_user.clusters.add(self.cluster)
        self.event = create_event(self.cluster, self.admin_user)
        self.guest = create_event_guest(self.event, self.admin_user)

    def test_list_event_guests(self):
        """
        Ensure guests for an event can be listed.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:eventguest-list", kwargs={"event_pk": self.event.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_check_in_guest(self):
        """
        Ensure a guest can be checked in.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:eventguest-check-in",
            kwargs={"event_pk": self.event.pk, "pk": self.guest.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.status, EventGuest.Status.ATTENDED)

    def test_check_out_guest(self):
        """
        Ensure a guest can be checked out.
        """
        self.guest.status = EventGuest.Status.ATTENDED
        self.guest.save()
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:eventguest-check-out",
            kwargs={"event_pk": self.event.pk, "pk": self.guest.pk},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertIsNotNone(self.guest.check_out_time)

    def test_create_event_guest(self):
        """
        Ensure an admin can create an event guest.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("management:eventguest-list", kwargs={"event_pk": self.event.pk})
        data = {"name": "New Guest"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_event_guest(self):
        """
        Ensure an admin can retrieve an event guest.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:eventguest-detail",
            kwargs={"event_pk": self.event.pk, "pk": self.guest.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_event_guest(self):
        """
        Ensure an admin can update an event guest.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:eventguest-detail",
            kwargs={"event_pk": self.event.pk, "pk": self.guest.pk},
        )
        data = {"name": "Updated Guest Name"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.name, "Updated Guest Name")

    def test_delete_event_guest(self):
        """
        Ensure an admin can delete an event guest.
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse(
            "management:eventguest-detail",
            kwargs={"event_pk": self.event.pk, "pk": self.guest.pk},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
