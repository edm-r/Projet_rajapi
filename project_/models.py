from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from datetime import datetime, date

class Project(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('archived', 'Archived')
    ]
    
    reference_number = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    objectives = models.TextField()
    deadline = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='in_progress')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='owned_projects'
    )
    start_date = models.DateField()
    location = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_number} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            year = timezone.now().strftime('%Y')
            unique_id = str(uuid.uuid4().int)[:5]
            self.reference_number = f"RJPC-{year}-{unique_id}"
        super().save(*args, **kwargs)

class ProjectDocument(models.Model):
    DOCUMENT_TYPES = [
        ('pdf', 'PDF'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('other', 'Other')
    ]
    
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='documents'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    document_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='project_documents/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='uploaded_documents'
    )
    version = models.PositiveIntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.project.reference_number}"

    def save(self, *args, **kwargs):
        if not self.pk:
            last_version = ProjectDocument.objects.filter(
                project=self.project,
                title=self.title
            ).order_by('-version').first()
            
            if last_version:
                self.version = last_version.version + 1
        
        super().save(*args, **kwargs)
        
        if not hasattr(self, '_skip_log'):
            ProjectChangeLog.objects.create(
                project=self.project,
                user=self.uploaded_by,
                action='document_added' if self.version == 1 else 'document_updated',
                changes={
                    'document_id': self.id,
                    'title': self.title,
                    'version': self.version,
                    'document_type': self.document_type
                },
                description=f"{'Ajout' if self.version == 1 else 'Mise à jour'} du document: {self.title} (v{self.version})"
            )

class ProjectChangeLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('restore', 'Restauration'),
        ('task_added', 'Ajout de tâche'),
        ('task_updated', 'Modification de tâche'),
        ('task_deleted', 'Suppression de tâche'),
        ('member_added', 'Ajout de membre'),
        ('member_removed', 'Retrait de membre'),
        ('document_added', 'Ajout de document'),
        ('document_updated', 'Mise à jour de document'),
        ('document_removed', 'Retrait de document')
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    changes = models.JSONField(help_text="Modifications apportées")
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.get_action_display()} - {self.project.reference_number} par {self.user.username if self.user else 'Système'}"

class Task(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed')
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=100)
    description = models.TextField()
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_tasks'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    due_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.project.reference_number}"

class ProjectMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('collaborator', 'Collaborator'),
        ('viewer', 'Viewer')
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('invited', 'Invited'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive')
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user_email = models.EmailField()  # Remplacer le ForeignKey par un EmailField
    username = models.CharField(max_length=150, blank=True, null=True)  # Ajout du champ username
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    joined_at = models.DateField(auto_now_add=True)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')

    class Meta:
        unique_together = ['project', 'user_email']

    def __str__(self):
        return f"{self.user_email} - {self.role} - {self.project.reference_number}"