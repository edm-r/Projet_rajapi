from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Project, ProjectMember, Task, 
    ProjectDocument, ProjectChangeLog
)

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDocument
        fields = [
            'id', 'title', 'description', 'document_type', 
            'file', 'file_url', 'version', 'uploaded_by', 
            'uploaded_by_details', 'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['uploaded_by', 'version', 'uploaded_at', 'updated_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None

class TaskSerializer(serializers.ModelSerializer):
    assigned_to = serializers.EmailField(required=False, allow_null=True)
    assigned_by_details = UserSerializer(source='assigned_by', read_only=True)
    assigned_to_email = serializers.SerializerMethodField(read_only=True)
    status = serializers.ChoiceField(choices=['open', 'closed'], required=False)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'assigned_to',
            'due_date', 'status', 'created_at', 'updated_at',
            'assigned_by_details', 'assigned_to_email'
        ]
        read_only_fields = ['created_at', 'updated_at', 'assigned_by']
        extra_kwargs = {
            'title': {'required': False},
            'description': {'required': False},
            'due_date': {'required': False}
        }

    def get_assigned_to_email(self, obj):
        if obj.assigned_to:
            return {
                'email': obj.assigned_to
            }
        return None

    def validate_assigned_to(self, value):
        """
        Vérifie que l'utilisateur assigné est un membre du projet.
        """
        if value is None:
            return None

        project = self.context.get('project')
        if not project:
            raise serializers.ValidationError("Le projet n'a pas été trouvé dans le contexte.")

        try:
            member = project.members.get(user_email=value, status='active')
            return member.user_email
        except ProjectMember.DoesNotExist:
            raise serializers.ValidationError("Le collaborateur n'est pas un membre du projet.")

    def validate(self, attrs):
        """
        Validation supplémentaire pour s'assurer que les champs requis sont présents lors de la création
        """
        if self.instance is None:  # C'est une création
            required_fields = ['title', 'description', 'due_date']
            missing_fields = [field for field in required_fields if field not in attrs]
            if missing_fields:
                raise serializers.ValidationError({
                    field: ["Ce champ est obligatoire."] for field in missing_fields
                })
        return attrs

class ProjectMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user_email')
    username = serializers.CharField(read_only=True)  # Ajout du champ username

    class Meta:
        model = ProjectMember
        fields = ['id', 'email', 'username', 'role', 'joined_at', 'status']  # Ajout de 'username'
        read_only_fields = ['joined_at', 'username']  # 'username' est en lecture seule

class ProjectChangeLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ProjectChangeLog
        fields = [
            'id', 'action', 'action_display', 'timestamp', 
            'changes', 'description', 'user_details'
        ]
        read_only_fields = ['id', 'timestamp', 'action_display', 'user_details']

class ProjectVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    action = serializers.CharField()
    action_display = serializers.CharField()
    user = serializers.CharField()
    description = serializers.CharField()
    changes = serializers.JSONField()

class ProjectDetailSerializer(serializers.ModelSerializer):
    owner_details = UserSerializer(source='owner', read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    tasks = TaskSerializer(many=True, read_only=True)
    documents = ProjectDocumentSerializer(many=True, read_only=True)
    current_version = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'reference_number', 'title', 'description', 
            'objectives', 'deadline', 'status', 'owner',
            'start_date', 'location', 'created_at', 'updated_at',
            'owner_details', 'members', 'tasks', 'documents', 
            'current_version'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at', 'reference_number']

    def get_current_version(self, obj):
        return obj.logs.count()

class ProjectListSerializer(serializers.ModelSerializer):
    owner_details = UserSerializer(source='owner', read_only=True)
    version_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'reference_number', 'title', 'status', 
            'start_date', 'deadline', 'location', 'created_at', 
            'owner_details', 'version_count', 'document_count'
        ]

    def get_version_count(self, obj):
        return obj.logs.count()

    def get_document_count(self, obj):
        return obj.documents.count()

class ProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'title', 'description', 'objectives', 'deadline',
            'status', 'start_date', 'location'
        ]

    def validate(self, data):
        if 'start_date' in data and 'deadline' in data:
            if data['start_date'] > data['deadline']:
                raise serializers.ValidationError(
                    "La date de fin doit être postérieure à la date de début"
                )
        return data

class RestoreVersionSerializer(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)