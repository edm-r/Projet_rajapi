from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db import transaction

from ..models import Task, Project, ProjectChangeLog
from ..serializers import TaskSerializer
from ..permissions import IsProjectMember
from .mixins import ChangeLogMixin

class TaskViewSet(ChangeLogMixin, viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'assigned_to']
    ordering_fields = ['due_date', 'created_at']

    def get_queryset(self):
        return Task.objects.filter(project_id=self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        project = get_object_or_404(Project, id=self.kwargs['project_pk'])
        context['project'] = project
        return context

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_pk'])
        
        task = serializer.save(
            project=project,
            assigned_by=self.request.user
        )

        self._log_change(
            project=project,
            action='task_added',
            changes={
                'task_id': task.id,
                'title': task.title,
                'assigned_to': task.assigned_to
            },
            description=f"Ajout de la tâche: {task.title}"
        )

    def perform_update(self, serializer):
        task = serializer.instance
        old_status = task.status
        updated_task = serializer.save()

        if old_status != updated_task.status:
            self._log_change(
                project=task.project,
                action='task_updated',
                changes={
                    'task_id': task.id,
                    'title': task.title,
                    'status': {
                        'from': old_status,
                        'to': updated_task.status
                    }
                },
                description=f"Modification du statut de la tâche: {task.title}"
            )

    def perform_destroy(self, instance):
        project = instance.project
        with transaction.atomic():
            # Créer le log avant la suppression
            self._log_change(
                project=project,
                action='task_deleted',
                changes={
                    'task_id': instance.id,
                    'title': instance.title,
                    'description': instance.description,
                    'assigned_to': instance.assigned_to,
                    'status': instance.status
                },
                description=f"Suppression de la tâche: {instance.title}"
            )
            # Supprimer la tâche
            instance.delete()