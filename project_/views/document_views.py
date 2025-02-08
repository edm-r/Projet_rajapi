from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.forms.models import model_to_dict
from django.db import transaction

from ..models import ProjectDocument, Project, ProjectChangeLog
from ..serializers import ProjectDocumentSerializer
from ..permissions import IsProjectMember
from .mixins import ChangeLogMixin

class ProjectDocumentViewSet(ChangeLogMixin, viewsets.ModelViewSet):
    serializer_class = ProjectDocumentSerializer
    permission_classes = [IsAuthenticated, IsProjectMember]

    def get_queryset(self):
        return ProjectDocument.objects.filter(
            project_id=self.kwargs['project_pk']
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        project = get_object_or_404(Project, id=self.kwargs['project_pk'])
        with transaction.atomic():
            document = serializer.save(
                project=project,
                uploaded_by=self.request.user
            )

            self._log_change(
                project=project,
                action='document_added',
                changes={
                    'document_id': document.id,
                    'title': document.title,
                    'document_type': document.document_type
                },
                description=f"Ajout du document: {document.title}"
            )

    def perform_update(self, serializer):
        document = serializer.instance
        old_data = model_to_dict(document)
        
        with transaction.atomic():
            updated_document = serializer.save()
            
            self._log_change(
                project=document.project,
                action='document_updated',
                changes={
                    'document_id': document.id,
                    'title': document.title,
                    'old_version': old_data.get('version'),
                    'new_version': updated_document.version
                },
                description=f"Mise à jour du document: {document.title}"
            )

    def perform_destroy(self, instance):
        project = instance.project
        with transaction.atomic():
            self._log_change(
                project=project,
                action='document_removed',
                changes={
                    'document_id': instance.id,
                    'title': instance.title,
                    'version': instance.version
                },
                description=f"Suppression du document: {instance.title}"
            )
            instance.delete()
