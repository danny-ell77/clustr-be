# Generated migration for NotificationLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('common', '0005_add_maintenance_models'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text='UUID primary key',
                        primary_key=True,
                        serialize=False,
                        verbose_name='id',
                    ),
                ),
                (
                    'created_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        editable=False,
                        verbose_name='creation date',
                    ),
                ),
                (
                    'created_by',
                    models.UUIDField(
                        editable=False,
                        help_text='the Id of the ClustR account user who added this object.',
                        null=True,
                        verbose_name='created by',
                    ),
                ),
                (
                    'last_modified_at',
                    models.DateTimeField(
                        auto_now=True,
                        editable=False,
                        verbose_name='last modified date',
                    ),
                ),
                (
                    'last_modified_by',
                    models.UUIDField(
                        editable=False,
                        help_text='the Id of the ClustR account user who last modified this object.',
                        null=True,
                        verbose_name='last modified by',
                    ),
                ),
                (
                    'event',
                    models.CharField(
                        help_text='Name of the notification event',
                        max_length=50,
                        verbose_name='event',
                    ),
                ),
                (
                    'channel',
                    models.CharField(
                        default='EMAIL',
                        help_text='Channel used to send the notification (EMAIL, SMS, etc.)',
                        max_length=20,
                        verbose_name='channel',
                    ),
                ),
                (
                    'success',
                    models.BooleanField(
                        default=False,
                        help_text='Whether the notification was sent successfully',
                        verbose_name='success',
                    ),
                ),
                (
                    'error_message',
                    models.TextField(
                        blank=True,
                        help_text='Error message if notification failed',
                        null=True,
                        verbose_name='error message',
                    ),
                ),
                (
                    'context_data',
                    models.JSONField(
                        default=dict,
                        help_text='Context data used for the notification',
                        verbose_name='context data',
                    ),
                ),
                (
                    'sent_at',
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text='When the notification was sent',
                        verbose_name='sent at',
                    ),
                ),
                (
                    'cluster',
                    models.ForeignKey(
                        help_text='The cluster this notification belongs to',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notification_logs',
                        to='common.cluster',
                        verbose_name='cluster',
                    ),
                ),
                (
                    'recipient',
                    models.ForeignKey(
                        help_text='User who received the notification',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='received_notifications',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='recipient',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Notification Log',
                'verbose_name_plural': 'Notification Logs',
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['cluster', 'event'], 
                name='notif_log_cluster_event_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['cluster', 'recipient'], 
                name='notif_log_cluster_recipient_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['cluster', 'sent_at'], 
                name='notif_log_cluster_sent_at_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['event', 'sent_at'], 
                name='notif_log_event_sent_at_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['recipient', 'sent_at'], 
                name='notif_log_recipient_sent_at_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='notificationlog',
            index=models.Index(
                fields=['success', 'sent_at'], 
                name='notif_log_success_sent_at_idx'
            ),
        ),
    ]