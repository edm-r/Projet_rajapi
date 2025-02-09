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
    assigned_to = serializers.SlugRelatedField(
        slug_field='username',
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
        error_messages={'does_not_exist': 'Collaborator don\'t exist.'}
    )
    assigned_to_details = UserSerializer(source='assigned_to', read_only=True)
    assigned_by_details = UserSerializer(source='assigned_by', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'assigned_to', 'assigned_by',
            'due_date', 'status', 'created_at', 'updated_at',
            'assigned_to_details', 'assigned_by_details'
        ]
        read_only_fields = ['created_at', 'updated_at', 'assigned_by']

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = serializers.EmailField()
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'role', 'joined_at', 'status', 'user_details']
        read_only_fields = ['joined_at', 'user_details']

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