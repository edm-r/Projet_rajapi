from django.urls import path, include
from rest_framework_nested import routers
from .views import (
    ProjectViewSet, TaskViewSet, ProjectDocumentViewSet
)

router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

projects_router = routers.NestedDefaultRouter(router, r'projects', lookup='project')
projects_router.register(r'tasks', TaskViewSet, basename='project-tasks')
projects_router.register(r'documents', ProjectDocumentViewSet, basename='project-documents')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
]