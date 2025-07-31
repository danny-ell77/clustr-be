# Generated migration for BillDispute model

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        # Create BillDispute model
        migrations.CreateModel(
            name='BillDispute',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='created at')),
                ('last_modified_at', models.DateTimeField(auto_now=True, verbose_name='last modified at')),
                ('reason', models.TextField(help_text='Detailed reason for disputing the bill', verbose_name='dispute reason')),
                ('status', models.CharField(choices=[('open', 'Open'), ('under_review', 'Under Review'), ('resolved', 'Resolved'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn')], default='open', help_text='Current status of the dispute', max_length=20, verbose_name='status')),
                ('admin_notes', models.TextField(blank=True, help_text='Internal notes from administrators', null=True, verbose_name='admin notes')),
                ('resolved_at', models.DateTimeField(blank=True, help_text='Date and time when dispute was resolved', null=True, verbose_name='resolved at')),
                ('resolution_notes', models.TextField(blank=True, help_text='Notes about how the dispute was resolved', null=True, verbose_name='resolution notes')),
                ('bill', models.ForeignKey(help_text='The bill being disputed', on_delete=django.db.models.deletion.CASCADE, related_name='disputes', to='common.bill', verbose_name='bill')),
                ('cluster', models.ForeignKey(help_text='The cluster this dispute belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='bill_disputes', to='common.cluster', verbose_name='cluster')),
                ('disputed_by', models.ForeignKey(help_text='User who raised the dispute', on_delete=django.db.models.deletion.CASCADE, related_name='bill_disputes', to='accounts.accountuser', verbose_name='disputed by')),
                ('resolved_by', models.ForeignKey(blank=True, help_text='Administrator who resolved the dispute', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resolved_disputes', to='accounts.accountuser', verbose_name='resolved by')),
            ],
            options={
                'verbose_name': 'Bill Dispute',
                'verbose_name_plural': 'Bill Disputes',
                'ordering': ['-created_at'],
                'default_permissions': [],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='billdispute',
            index=models.Index(fields=['cluster', 'bill'], name='common_billdispute_cluster_bill_idx'),
        ),
        migrations.AddIndex(
            model_name='billdispute',
            index=models.Index(fields=['disputed_by'], name='common_billdispute_disputed_by_idx'),
        ),
        migrations.AddIndex(
            model_name='billdispute',
            index=models.Index(fields=['status'], name='common_billdispute_status_idx'),
        ),
        migrations.AddIndex(
            model_name='billdispute',
            index=models.Index(fields=['created_at'], name='common_billdispute_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='billdispute',
            index=models.Index(fields=['resolved_at'], name='common_billdispute_resolved_at_idx'),
        ),
        
        # Add unique constraint
        migrations.AddConstraint(
            model_name='billdispute',
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=['open', 'under_review']),
                fields=['bill', 'disputed_by'],
                name='unique_bill_dispute_per_user'
            ),
        ),
        
        # Remove old dispute fields from Bill model
        migrations.RemoveField(
            model_name='bill',
            name='dispute_reason',
        ),
        migrations.RemoveField(
            model_name='bill',
            name='disputed_at',
        ),
        
        # Remove old index
        migrations.RemoveIndex(
            model_name='bill',
            name='common_bill_dispute_68ca65_idx',
        ),
    ]