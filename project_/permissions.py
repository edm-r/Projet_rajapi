from rest_framework import permissions

class IsProjectOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'project'):
            return obj.project.owner == request.user
        return obj.owner == request.user

class IsProjectMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'project'):
            project = obj.project
        else:
            project = obj
        return project.members.filter(user=request.user).exists()

class HasProjectRole(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
            
        project = obj if hasattr(obj, 'owner') else obj.project
        member = project.members.filter(user=request.user).first()
        
        if not member:
            return False
            
        if member.role == 'owner':
            return True
            
        if member.role == 'collaborator':
            return request.method != 'DELETE'
            
        return False