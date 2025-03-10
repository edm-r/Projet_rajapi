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
import requests

from ..models import (
    Project, ProjectMember, ProjectChangeLog, 
    ProjectDocument
)
from ..serializers import (
    ProjectDetailSerializer, ProjectListSerializer,
    ProjectMemberSerializer, ProjectUpdateSerializer,
    RestoreVersionSerializer, ProjectDocumentSerializer
)
from ..permissions import IsProjectOwner, IsProjectMember, HasProjectRole
from .mixins import ChangeLogMixin
from ..authentication import MicroserviceTokenAuthentication
from ..services import ProjectMemberService

User = get_user_model()

class ProjectViewSet(ChangeLogMixin, viewsets.ModelViewSet):
    authentication_classes = [MicroserviceTokenAuthentication]
    permission_classes = [IsAuthenticated, HasProjectRole]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'location']
    search_fields = ['title', 'description', 'objectives', 'reference_number']
    ordering_fields = ['created_at', 'deadline']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.member_service = ProjectMemberService()

    def get_queryset(self):
        if self.request.user.is_staff:
            return Project.objects.all()
            
        # Vérifier le statut du membre avant de retourner les projets
        auth_header = self.request.headers.get('Authorization')
        projects = Project.objects.filter(
            members__user_email=self.request.user.email,
            members__status='active'
        )
        
        # Vérifier le statut du membre pour chaque projet
        for project in projects:
            member = project.members.get(
                user_email=self.request.user.email,
                status='active'
            )
            self.member_service.verify_member(member, auth_header)
            
        # Requête mise à jour après vérifications
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
            
            # Créer le membre propriétaire
            ProjectMember.objects.create(
                project=project,
                user_email=self.request.user.email,
                role='owner',
                status='active',
                joined_at=timezone.now().date(),
                last_verified_at=timezone.now()
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

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Ajouter un membre au projet avec vérification via microservice d'authentification"""
        project = self.get_object()
        
        if not IsProjectOwner().has_object_permission(request, self, project):
            return Response(
                {
                    "code": "PERMISSION_DENIED",
                    "detail": "Seul le propriétaire peut ajouter des membres."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectMemberSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "code": "VALIDATION_ERROR",
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['user_email']
        role = serializer.validated_data.get('role', 'collaborator')
        auth_header = request.headers.get('Authorization')

        # Vérifier si l'utilisateur existe dans le service d'auth et récupérer son profil
        try:
            user_profile = self.member_service.auth_service.get_user_profile(email, auth_header)
            username = user_profile.get('username')  # Récupérer le username depuis le profil

            with transaction.atomic():
                member, created = ProjectMember.objects.get_or_create(
                    project=project,
                    user_email=email,
                    defaults={
                        'role': role,
                        'status': 'active',
                        'last_verified_at': timezone.now(),
                        'username': username  # Ajout du username
                    }
                )

                if not created:
                    if member.status == 'inactive':
                        member.status = 'active'
                        member.role = role
                        member.last_verified_at = timezone.now()
                        member.username = username  # Mise à jour du username
                        member.save()
                    else:
                        return Response(
                            {
                                "code": "USER_ALREADY_MEMBER",
                                "detail": "L'utilisateur est déjà membre du projet."
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )

                self._log_change(
                    project=project,
                    action='member_added',
                    changes={'email': email, 'role': role, 'username': username},
                    description=f"Ajout du membre {email} (username: {username}) avec le rôle {role}"
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
                    "code": "AUTH_SERVICE_ERROR",
                    "detail": "Erreur de communication avec le service d'authentification."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

    @action(detail=True, methods=['delete'])
    def remove_member(self, request, pk=None):
        project = self.get_object()
        if not IsProjectOwner().has_object_permission(request, self, project):
            return Response(
                {
                    "code": "PERMISSION_DENIED",
                    "detail": "Seul le propriétaire peut retirer des membres."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.query_params.get('email')
        if not email:
            return Response(
                {
                    "code": "MISSING_EMAIL",
                    "detail": "L'email de l'utilisateur est requis."
                },
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
                    {
                        "code": "CANNOT_REMOVE_OWNER",
                        "detail": "Impossible de retirer le propriétaire du projet."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            member.status = 'inactive'
            member.save()
            
            self._log_change(
                project=project,
                action='member_removed',
                changes={'email': email},
                description=f"Retrait du membre {email}"
            )
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProjectMember.DoesNotExist:
            return Response(
                {
                    "code": "MEMBER_NOT_FOUND",
                    "detail": "Membre non trouvé."
                },
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['post'])
    def verify_members(self, request, pk=None):
        """Vérifie le statut de tous les membres du projet"""
        project = self.get_object()
        
        if not IsProjectOwner().has_object_permission(request, self, project):
            return Response(
                {
                    "code": "PERMISSION_DENIED",
                    "detail": "Seul le propriétaire peut vérifier les membres."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        auth_header = request.headers.get('Authorization')
        results = self.member_service.verify_all_members(project, auth_header)

        if results['deactivated']:
            self._log_change(
                project=project,
                action='member_removed',
                changes={'deactivated_members': results['deactivated']},
                description=f"Membres désactivés suite à la vérification: {', '.join(results['deactivated'])}"
            )

        return Response({
            "message": "Vérification des membres terminée",
            "results": results
        })
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Liste tous les membres d'un projet avec leur statut de vérification"""
        project = self.get_object()
        
        # Vérifier que l'utilisateur est membre du projet
        if not IsProjectMember().has_object_permission(request, self, project):
            return Response(
                {
                    "code": "PERMISSION_DENIED",
                    "detail": "Vous n'êtes pas autorisé à voir les membres de ce projet."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Optionnel : paramètre pour filtrer par statut
        status_filter = request.query_params.get('status', None)
        members = project.members.all()
        
        if status_filter:
            members = members.filter(status=status_filter)

        # Préparer les données des membres avec des informations supplémentaires
        members_data = []
        auth_header = request.headers.get('Authorization')
        
        for member in members:
            member_data = ProjectMemberSerializer(member).data
            
            # Ajouter des informations supplémentaires si le membre est actif
            if member.status == 'active':
                try:
                    user_profile = self.member_service.auth_service.get_user_profile(
                        member.user_email, 
                        auth_header
                    )
                    member_data.update({
                        'full_name': f"{user_profile.get('first_name', '')} {user_profile.get('last_name', '')}".strip(),
                        'last_verified': member.last_verified_at.isoformat() if member.last_verified_at else None
                    })
                except requests.RequestException:
                    # En cas d'erreur, on continue avec les données de base
                    member_data.update({
                        'full_name': member.user_email,
                        'last_verified': member.last_verified_at.isoformat() if member.last_verified_at else None
                    })
            
            members_data.append(member_data)

        # Trier les membres : propriétaire en premier, puis par rôle et email
        members_data.sort(key=lambda x: (
            x['role'] != 'owner',  # propriétaire en premier
            {
                'owner': 0,
                'collaborator': 1,
                'viewer': 2
            }.get(x['role'], 3),  # puis par rôle
            x['email']  # puis par email
        ))

        return Response({
            'project': {
                'id': project.id,
                'reference_number': project.reference_number,
                'title': project.title
            },
            'members_count': len(members_data),
            'members': members_data,
        })

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
            return Response({
                "code": "VALIDATION_ERROR",
                "detail": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        target_version = serializer.validated_data['version']
        logs = project.logs.all().order_by('timestamp')

        if target_version > logs.count():
            return Response(
                {
                    "code": "VERSION_NOT_FOUND",
                    "detail": f"La version {target_version} n'existe pas. Version max: {logs.count()}"
                },
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

            # Logger la restauration
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

    @action(detail=True, methods=['post'])
    def upload_documents(self, request, pk=None):
        """Upload un ou plusieurs documents"""
        project = self.get_object()
        if not IsProjectMember().has_object_permission(request, self, project):
            return Response(
                {
                    "code": "PERMISSION_DENIED",
                    "detail": "Seuls les membres du projet peuvent uploader des documents."
                },
                status=status.HTTP_403_FORBIDDEN
            )

        files = request.FILES.getlist('documents')
        if not files:
            return Response(
                {
                    "code": "NO_DOCUMENTS_PROVIDED",
                    "detail": "Aucun document fourni."
                },
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