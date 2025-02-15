# Generated by Django 5.1.3 on 2025-02-15 22:20

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference_number', models.CharField(editable=False, max_length=20, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('objectives', models.TextField()),
                ('deadline', models.DateField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('in_progress', 'In Progress'), ('done', 'Done'), ('archived', 'Archived')], default='in_progress', max_length=50)),
                ('start_date', models.DateField()),
                ('location', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_projects', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Création'), ('update', 'Modification'), ('delete', 'Suppression'), ('restore', 'Restauration'), ('task_added', 'Ajout de tâche'), ('task_updated', 'Modification de tâche'), ('task_deleted', 'Suppression de tâche'), ('member_added', 'Ajout de membre'), ('member_removed', 'Retrait de membre'), ('document_added', 'Ajout de document'), ('document_updated', 'Mise à jour de document'), ('document_removed', 'Retrait de document')], max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('changes', models.JSONField(help_text='Modifications apportées')),
                ('description', models.TextField(blank=True, null=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='project_.project')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['timestamp'],
            },
        ),
        migrations.CreateModel(
            name='ProjectDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('document_type', models.CharField(choices=[('pdf', 'PDF'), ('image', 'Image'), ('video', 'Video'), ('other', 'Other')], max_length=10)),
                ('file', models.FileField(upload_to='project_documents/')),
                ('version', models.PositiveIntegerField(default=1)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='project_.project')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_documents', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('assigned_to', models.EmailField(blank=True, max_length=254, null=True)),
                ('due_date', models.DateField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_tasks', to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='project_.project')),
            ],
        ),
        migrations.CreateModel(
            name='ProjectMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_email', models.EmailField(max_length=254)),
                ('username', models.CharField(blank=True, max_length=150, null=True)),
                ('role', models.CharField(choices=[('owner', 'Owner'), ('collaborator', 'Collaborator'), ('viewer', 'Viewer')], max_length=50)),
                ('joined_at', models.DateField(auto_now_add=True)),
                ('last_verified_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('invited', 'Invited'), ('pending', 'Pending'), ('inactive', 'Inactive')], default='active', max_length=50)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='members', to='project_.project')),
            ],
            options={
                'unique_together': {('project', 'user_email')},
            },
        ),
    ]
