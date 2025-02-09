from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.forms.models import model_to_dict
from django.db import transaction
from datetime import datetime, date
from django.contrib.auth import get_user_model
from ..models import Project, ProjectMember, ProjectChangeLog, ProjectDocument
from ..serializers import (
    ProjectDetailSerializer, ProjectListSerializer,
    ProjectMemberSerializer, ProjectUpdateSerializer,
    RestoreVersionSerializer, ProjectDocumentSerializer
)
import requests
from ..permissions import IsProjectOwner, IsProjectMember, HasProjectRole
from .mixins import ChangeLogMixin
from ..authentication import MicroserviceTokenAuthentication
User = get_user_model()
class ProjectViewSet(ChangeLogMixin, viewsets.ModelViewSet):
    authentication_classes = [MicroserviceTokenAuthentication]
    permission_classes = [IsAuthenticated, HasProjectRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'location']
    search_fields = ['title', 'description', 'objectives', 'reference_number']
    ordering_fields = ['created_at', 'deadline']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Project.objects.all()
        return Project.objects.filter(
            members__user_email=self.request.user.email,
            members__status='active'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        if self.action in ['update', 'partial_update']:
            return ProjectUpdateSerializer
        return ProjectDetailSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            project = serializer.save(owner=self.request.user)
            
            ProjectMember.objects.create(
                project=project,
                user_email=self.request.user.email,
                role='owner',
                status='active',
                joined_at=timezone.now().date()
            )
            
            self._log_change(
                project=project,
                action='create',
                changes=serializer.data,
                description="Création initiale du projet"
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            project = serializer.instance
            old_data = model_to_dict(project)
            changes = self._get_field_changes(old_data, serializer.validated_data)

            if changes:
                project = serializer.save()
                self._log_change(
                    project=project,
                    action='update',
                    changes=changes,
                    description=self.request.data.get('description', 'Mise à jour du projet')
                )

    def perform_destroy(self, instance):
        with transaction.atomic():
            self._log_change(
                project=instance,
                action='delete',
                changes={},
                description="Suppression du projet"
            )
            instance.delete()

    # Actions pour la gestion des membres
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Ajouter un membre au projet avec vérification via microservice d'authentification"""
        project = self.get_object()
        
        # Vérifier les permissions
        if not IsProjectOwner().has_object_permission(request, self, project):
            return Response(
                {"error": "Seul le propriétaire peut ajouter des membres"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Valider les données d'entrée
        serializer = ProjectMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['user_email']
        role = serializer.validated_data.get('role', 'collaborator')

        # Vérifier si l'utilisateur existe déjà dans le projet
        existing_member = ProjectMember.objects.filter(
            project=project,
            user_email=email
        ).first()

        if existing_member:
            if existing_member.status == 'inactive':
                existing_member.status = 'active'
                existing_member.role = role
                existing_member.save()
                return Response(
                    {"message": "Membre réactivé avec succès"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"error": "L'utilisateur est déjà membre du projet"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer le token d'authentification
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return Response(
                {"error": "Token d'authentification manquant"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Vérifier l'utilisateur auprès du microservice d'authentification
        try:
            response = requests.get(
                "https://rajapi-cop-auth-api-33be22136f5e.herokuapp.com/auth/profile/",
                params={"email": email},
                headers={'Authorization': auth_header},
                timeout=10
            )

            if response.status_code != 200:
                return Response(
                    {"error": "Utilisateur non trouvé ou non autorisé"},
                    status=response.status_code
                )

            # Créer le membre avec transaction atomique
            with transaction.atomic():
                member = ProjectMember.objects.create(
                    project=project,
                    user_email=email,
                    role=role,
                    status='active'
                )

                # Logger le changement
                project.logs.create(
                    user=request.user,
                    action='member_added',
                    changes={
                        'email': email,
                        'role': role
                    },
                    description=f"Ajout du membre {email} avec le rôle {role}"
                )

                return Response(
                    {
                        "message": "Membre ajouté avec succès",
                        "member": ProjectMemberSerializer(member).data
                    },
                    status=status.HTTP_201_CREATED
                )

        except requests.RequestException as e:
            return Response(
                {
                    "error": "Erreur de communication avec le service d'authentification",
                    "detail": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        project = self.get_object()
        if not IsProjectOwner().has_object_permission(request, self, project):
            return Response(
                {"error": "Seul le propriétaire peut retirer des membres"},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.query_params.get('email')  # Changé de user_id à email
        if not email:
            return Response(
                {"error": "L'email de l'utilisateur est requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            member = ProjectMember.objects.get(
                project=project, 
                user_email=email,
                status='active'
            )
            if member.role == 'owner':
                return Response(
                    {"error": "Impossible de retirer le propriétaire du projet"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Au lieu de supprimer, on met à jour le statut
            member.status = 'inactive'
            member.save()
            
            # Logger le changement
            self._log_change(
                project=project,
                action='member_removed',
                changes={'email': email},
                description=f"Retrait du membre {email}"
            )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProjectMember.DoesNotExist:
            return Response(
                {"error": "Membre non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )


    # Actions pour la gestion des versions
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Liste toutes les versions du projet"""
        project = self.get_object()
        logs = project.logs.all().order_by('timestamp')
        
        versions = []
        for index, log in enumerate(logs, start=1):
            versions.append({
                'version': index,
                'timestamp': log.timestamp,
                'action': log.action,
                'action_display': log.get_action_display(),
                'user': log.user.get_full_name() if log.user else "Système",
                'description': log.description,
                'changes': log.changes
            })

        return Response({
            "project": ProjectListSerializer(project).data,
            "versions": versions
        })

    @action(detail=True, methods=['post'])
    def restore_version(self, request, pk=None):
        """Restaure le projet à une version spécifique"""
        project = self.get_object()
        serializer = RestoreVersionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_version = serializer.validated_data['version']
        logs = project.logs.all().order_by('timestamp')

        if target_version > logs.count():
            return Response(
                {"error": f"La version {target_version} n'existe pas. Version max: {logs.count()}"},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            # Sauvegarder l'état actuel
            current_state = model_to_dict(
                project, 
                exclude=['owner', 'members', 'tasks', 'documents']
            )
            
            # Convertir les dates en string dans l'état actuel
            for key, value in current_state.items():
                if isinstance(value, (date, datetime)):
                    current_state[key] = value.isoformat()

            # Reconstruire l'état à la version cible
            restored_state = {}
            for log in logs[:target_version]:
                if log.action == 'create':
                    changes = {
                        k: v for k, v in log.changes.items() 
                        if k not in ['owner', 'members', 'tasks', 'documents']
                    }
                    restored_state.update(changes)
                elif log.action == 'update':
                    for field, change in log.changes.items():
                        if (field not in ['owner', 'members', 'tasks', 'documents'] 
                            and 'to' in change):
                            restored_state[field] = change['to']

            # Appliquer l'état restauré
            for field, value in restored_state.items():
                if hasattr(project, field) and field not in [
                    'owner', 'members', 'tasks', 'documents'
                ]:
                    if field in ['start_date', 'deadline'] and isinstance(value, str):
                        try:
                            value = datetime.fromisoformat(value).date()
                        except (ValueError, TypeError):
                            continue
                    setattr(project, field, value)
            
            project.save()

            # Logger la restauration avec conversion JSON
            self._log_change(
                project=project,
                action='restore',
                changes={
                    'restored_to_version': target_version,
                    'previous_state': current_state,
                    'restored_state': restored_state
                },
                description=f"Restauration à la version {target_version}"
            )

        return Response({
            "message": f"Projet restauré à la version {target_version}",
            "project": ProjectDetailSerializer(project).data
        })

    # Gestion des documents
    @action(detail=True, methods=['post'])
    def upload_documents(self, request, pk=None):
        """Upload un ou plusieurs documents"""
        project = self.get_object()
        if not IsProjectMember().has_object_permission(request, self, project):
            return Response(
                {"error": "Seuls les membres du projet peuvent uploader des documents"},
                status=status.HTTP_403_FORBIDDEN
            )

        files = request.FILES.getlist('documents')
        if not files:
            return Response(
                {"error": "Aucun document fourni"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_documents = []
        for file in files:
            doc = ProjectDocument.objects.create(
                project=project,
                title=request.data.get('title', file.name),
                description=request.data.get('description'),
                document_type=request.data.get('document_type', 'other'),
                file=file,
                uploaded_by=request.user
            )
            created_documents.append(doc)

        serializer = ProjectDocumentSerializer(
            created_documents,
            many=True,
            context={'request': request}
        )
        return Response(
            {
                "message": f"{len(files)} document(s) uploadé(s) avec succès",
                "documents": serializer.data
            },
            status=status.HTTP_201_CREATED
        )
