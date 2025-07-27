# Generated manually for maintenance models

import uuid
import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0004_remove_cluster_admin_cluster_owner_id'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID primary key', primary_key=True, serialize=False, verbose_name='id')),
                ('created_at', models.DateTimeField(auto_now_add=True, editable=False, verbose_name='creation date')),
                ('created_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who added this object.', null=True, verbose_name='created by')),
                ('last_modified_at', models.DateTimeField(auto_now=True, editable=False, verbose_name='last modified date')),
                ('last_modified_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who last modified this object.', null=True, verbose_name='last modified by')),
                ('maintenance_number', models.CharField(help_text='Unique maintenance number for tracking', max_length=20, unique=True, verbose_name='maintenance number')),
                ('title', models.CharField(help_text='Brief title describing the maintenance activity', max_length=200, verbose_name='maintenance title')),
                ('description', models.TextField(help_text='Detailed description of the maintenance work performed', verbose_name='description')),
                ('maintenance_type', models.CharField(choices=[('PREVENTIVE', 'Preventive'), ('CORRECTIVE', 'Corrective'), ('EMERGENCY', 'Emergency'), ('ROUTINE', 'Routine'), ('INSPECTION', 'Inspection'), ('UPGRADE', 'Upgrade'), ('OTHER', 'Other')], default='ROUTINE', help_text='Type of maintenance activity', max_length=20, verbose_name='maintenance type')),
                ('property_type', models.CharField(choices=[('BUILDING', 'Building'), ('ELECTRICAL', 'Electrical'), ('PLUMBING', 'Plumbing'), ('HVAC', 'HVAC'), ('SECURITY', 'Security'), ('LANDSCAPING', 'Landscaping'), ('EQUIPMENT', 'Equipment'), ('INFRASTRUCTURE', 'Infrastructure'), ('OTHER', 'Other')], default='OTHER', help_text='Type of property or equipment maintained', max_length=20, verbose_name='property type')),
                ('property_location', models.CharField(help_text='Specific location of the property or equipment', max_length=200, verbose_name='property location')),
                ('equipment_name', models.CharField(blank=True, help_text='Name or model of the equipment (if applicable)', max_length=200, verbose_name='equipment name')),
                ('priority', models.CharField(choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('URGENT', 'Urgent')], default='MEDIUM', help_text='Priority level of the maintenance', max_length=10, verbose_name='priority')),
                ('status', models.CharField(choices=[('SCHEDULED', 'Scheduled'), ('IN_PROGRESS', 'In Progress'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('POSTPONED', 'Postponed')], default='SCHEDULED', help_text='Current status of the maintenance', max_length=20, verbose_name='status')),
                ('scheduled_date', models.DateTimeField(blank=True, help_text='Scheduled date and time for the maintenance', null=True, verbose_name='scheduled date')),
                ('started_at', models.DateTimeField(blank=True, help_text='Timestamp when maintenance was started', null=True, verbose_name='started at')),
                ('completed_at', models.DateTimeField(blank=True, help_text='Timestamp when maintenance was completed', null=True, verbose_name='completed at')),
                ('estimated_duration', models.DurationField(blank=True, help_text='Estimated time to complete the maintenance', null=True, verbose_name='estimated duration')),
                ('actual_duration', models.DurationField(blank=True, help_text='Actual time spent on the maintenance', null=True, verbose_name='actual duration')),
                ('cost', models.DecimalField(blank=True, decimal_places=2, help_text='Total cost of the maintenance', max_digits=10, null=True, verbose_name='cost')),
                ('materials_used', models.TextField(blank=True, help_text='List of materials and parts used', verbose_name='materials used')),
                ('tools_used', models.TextField(blank=True, help_text='List of tools and equipment used', verbose_name='tools used')),
                ('notes', models.TextField(blank=True, help_text='Additional notes about the maintenance', verbose_name='notes')),
                ('completion_notes', models.TextField(blank=True, help_text='Notes about maintenance completion and results', verbose_name='completion notes')),
                ('next_maintenance_due', models.DateTimeField(blank=True, help_text='When the next maintenance is due for this item', null=True, verbose_name='next maintenance due')),
                ('warranty_expiry', models.DateField(blank=True, help_text='Warranty expiry date for the equipment', null=True, verbose_name='warranty expiry')),
                ('is_under_warranty', models.BooleanField(default=False, help_text='Whether the equipment is still under warranty', verbose_name='is under warranty')),
                ('cluster', models.ForeignKey(help_text='The cluster this object belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='maintenancelogs', related_query_name='maintenancelog', to='common.cluster', verbose_name='cluster')),
                ('performed_by', models.ForeignKey(blank=True, help_text='Staff member who performed the maintenance', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='performed_maintenance', to='accounts.accountuser', verbose_name='performed by')),
                ('requested_by', models.ForeignKey(help_text='User who requested the maintenance', on_delete=django.db.models.deletion.CASCADE, related_name='requested_maintenance', to='accounts.accountuser', verbose_name='requested by')),
                ('supervised_by', models.ForeignKey(blank=True, help_text='Staff member who supervised the maintenance', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='supervised_maintenance', to='accounts.accountuser', verbose_name='supervised by')),
            ],
            options={
                'verbose_name': 'maintenance log',
                'verbose_name_plural': 'maintenance logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='MaintenanceSchedule',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID primary key', primary_key=True, serialize=False, verbose_name='id')),
                ('created_at', models.DateTimeField(auto_now_add=True, editable=False, verbose_name='creation date')),
                ('created_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who added this object.', null=True, verbose_name='created by')),
                ('last_modified_at', models.DateTimeField(auto_now=True, editable=False, verbose_name='last modified date')),
                ('last_modified_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who last modified this object.', null=True, verbose_name='last modified by')),
                ('name', models.CharField(help_text='Name of the maintenance schedule', max_length=200, verbose_name='schedule name')),
                ('description', models.TextField(help_text='Description of the scheduled maintenance', verbose_name='description')),
                ('property_type', models.CharField(choices=[('BUILDING', 'Building'), ('ELECTRICAL', 'Electrical'), ('PLUMBING', 'Plumbing'), ('HVAC', 'HVAC'), ('SECURITY', 'Security'), ('LANDSCAPING', 'Landscaping'), ('EQUIPMENT', 'Equipment'), ('INFRASTRUCTURE', 'Infrastructure'), ('OTHER', 'Other')], help_text='Type of property or equipment', max_length=20, verbose_name='property type')),
                ('property_location', models.CharField(help_text='Specific location of the property or equipment', max_length=200, verbose_name='property location')),
                ('equipment_name', models.CharField(blank=True, help_text='Name or model of the equipment (if applicable)', max_length=200, verbose_name='equipment name')),
                ('frequency_type', models.CharField(choices=[('DAILY', 'Daily'), ('WEEKLY', 'Weekly'), ('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly'), ('SEMI_ANNUAL', 'Semi-Annual'), ('ANNUAL', 'Annual'), ('CUSTOM', 'Custom')], default='MONTHLY', help_text='How often the maintenance should be performed', max_length=20, verbose_name='frequency type')),
                ('frequency_value', models.PositiveIntegerField(default=1, help_text='Numeric value for custom frequency (e.g., every 3 months)', verbose_name='frequency value')),
                ('next_due_date', models.DateTimeField(help_text='When the next maintenance is due', verbose_name='next due date')),
                ('estimated_duration', models.DurationField(blank=True, help_text='Estimated time to complete the maintenance', null=True, verbose_name='estimated duration')),
                ('estimated_cost', models.DecimalField(blank=True, decimal_places=2, help_text='Estimated cost of the maintenance', max_digits=10, null=True, verbose_name='estimated cost')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this schedule is active', verbose_name='is active')),
                ('instructions', models.TextField(blank=True, help_text='Instructions for performing the maintenance', verbose_name='instructions')),
                ('materials_needed', models.TextField(blank=True, help_text='List of materials typically needed', verbose_name='materials needed')),
                ('tools_needed', models.TextField(blank=True, help_text='List of tools typically needed', verbose_name='tools needed')),
                ('assigned_to', models.ForeignKey(blank=True, help_text='Staff member assigned to this maintenance', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_maintenance_schedules', to='accounts.accountuser', verbose_name='assigned to')),
                ('cluster', models.ForeignKey(help_text='The cluster this object belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='maintenanceschedules', related_query_name='maintenanceschedule', to='common.cluster', verbose_name='cluster')),
            ],
            options={
                'verbose_name': 'maintenance schedule',
                'verbose_name_plural': 'maintenance schedules',
                'ordering': ['next_due_date'],
            },
        ),
        migrations.CreateModel(
            name='MaintenanceComment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID primary key', primary_key=True, serialize=False, verbose_name='id')),
                ('created_at', models.DateTimeField(auto_now_add=True, editable=False, verbose_name='creation date')),
                ('created_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who added this object.', null=True, verbose_name='created by')),
                ('last_modified_at', models.DateTimeField(auto_now=True, editable=False, verbose_name='last modified date')),
                ('last_modified_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who last modified this object.', null=True, verbose_name='last modified by')),
                ('content', models.TextField(help_text='Content of the comment', verbose_name='content')),
                ('is_internal', models.BooleanField(default=False, help_text='Whether this comment is internal (staff only)', verbose_name='is internal')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_comments', to='accounts.accountuser', verbose_name='author')),
                ('cluster', models.ForeignKey(help_text='The cluster this object belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='maintenancecomments', related_query_name='maintenancecomment', to='common.cluster', verbose_name='cluster')),
                ('maintenance_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='common.maintenancelog', verbose_name='maintenance log')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='common.maintenancecomment', verbose_name='parent comment')),
            ],
            options={
                'verbose_name': 'maintenance comment',
                'verbose_name_plural': 'maintenance comments',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='MaintenanceCost',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID primary key', primary_key=True, serialize=False, verbose_name='id')),
                ('created_at', models.DateTimeField(auto_now_add=True, editable=False, verbose_name='creation date')),
                ('created_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who added this object.', null=True, verbose_name='created by')),
                ('last_modified_at', models.DateTimeField(auto_now=True, editable=False, verbose_name='last modified date')),
                ('last_modified_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who last modified this object.', null=True, verbose_name='last modified by')),
                ('category', models.CharField(choices=[('LABOR', 'Labor'), ('MATERIALS', 'Materials'), ('EQUIPMENT', 'Equipment'), ('CONTRACTOR', 'Contractor'), ('PERMITS', 'Permits'), ('OTHER', 'Other')], default='OTHER', help_text='Category of the cost', max_length=50, verbose_name='cost category')),
                ('description', models.CharField(help_text='Description of the cost item', max_length=200, verbose_name='description')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, help_text='Quantity of the item', max_digits=10, verbose_name='quantity')),
                ('unit_cost', models.DecimalField(decimal_places=2, help_text='Cost per unit', max_digits=10, verbose_name='unit cost')),
                ('total_cost', models.DecimalField(decimal_places=2, help_text='Total cost (quantity × unit cost)', max_digits=10, verbose_name='total cost')),
                ('vendor', models.CharField(blank=True, help_text='Vendor or supplier name', max_length=200, verbose_name='vendor')),
                ('receipt_number', models.CharField(blank=True, help_text='Receipt or invoice number', max_length=100, verbose_name='receipt number')),
                ('date_incurred', models.DateField(default=timezone.now, help_text='Date when the cost was incurred', verbose_name='date incurred')),
                ('cluster', models.ForeignKey(help_text='The cluster this object belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='maintenancecosts', related_query_name='maintenancecost', to='common.cluster', verbose_name='cluster')),
                ('maintenance_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cost_breakdown', to='common.maintenancelog', verbose_name='maintenance log')),
            ],
            options={
                'verbose_name': 'maintenance cost',
                'verbose_name_plural': 'maintenance costs',
                'ordering': ['date_incurred'],
            },
        ),
        migrations.CreateModel(
            name='MaintenanceAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='UUID primary key', primary_key=True, serialize=False, verbose_name='id')),
                ('created_at', models.DateTimeField(auto_now_add=True, editable=False, verbose_name='creation date')),
                ('created_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who added this object.', null=True, verbose_name='created by')),
                ('last_modified_at', models.DateTimeField(auto_now=True, editable=False, verbose_name='last modified date')),
                ('last_modified_by', models.UUIDField(editable=False, help_text='the Id of the ClustR account user who last modified this object.', null=True, verbose_name='last modified by')),
                ('file_name', models.CharField(help_text='Original name of the uploaded file', max_length=255, verbose_name='file name')),
                ('file_url', models.URLField(help_text='URL to access the uploaded file', verbose_name='file URL')),
                ('file_size', models.PositiveIntegerField(help_text='Size of the file in bytes', verbose_name='file size')),
                ('file_type', models.CharField(help_text='MIME type of the file', max_length=100, verbose_name='file type')),
                ('attachment_type', models.CharField(choices=[('BEFORE', 'Before Photo'), ('DURING', 'During Work'), ('AFTER', 'After Photo'), ('RECEIPT', 'Receipt'), ('MANUAL', 'Manual'), ('DIAGRAM', 'Diagram'), ('OTHER', 'Other')], default='OTHER', help_text='Type of attachment', max_length=20, verbose_name='attachment type')),
                ('description', models.TextField(blank=True, help_text='Description of the attachment', verbose_name='description')),
                ('cluster', models.ForeignKey(help_text='The cluster this object belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='maintenanceattachments', related_query_name='maintenanceattachment', to='common.cluster', verbose_name='cluster')),
                ('maintenance_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='common.maintenancelog', verbose_name='maintenance log')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maintenance_attachments', to='accounts.accountuser', verbose_name='uploaded by')),
            ],
            options={
                'verbose_name': 'maintenance attachment',
                'verbose_name_plural': 'maintenance attachments',
                'ordering': ['created_at'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['maintenance_number'], name='common_main_mainten_b8b8b8_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['status'], name='common_main_status_a1a1a1_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['priority'], name='common_main_priority_c2c2c2_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['maintenance_type'], name='common_main_mainten_d3d3d3_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['property_type'], name='common_main_propert_e4e4e4_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['performed_by'], name='common_main_perform_f5f5f5_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['requested_by'], name='common_main_request_161616_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['scheduled_date'], name='common_main_schedul_272727_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['next_maintenance_due'], name='common_main_next_ma_383838_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancelog',
            index=models.Index(fields=['created_at'], name='common_main_created_494949_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenanceschedule',
            index=models.Index(fields=['next_due_date'], name='common_main_next_du_5a5a5a_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenanceschedule',
            index=models.Index(fields=['is_active'], name='common_main_is_acti_6b6b6b_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenanceschedule',
            index=models.Index(fields=['property_type'], name='common_main_propert_7c7c7c_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenanceschedule',
            index=models.Index(fields=['assigned_to'], name='common_main_assigne_8d8d8d_idx'),
        ),
    ]