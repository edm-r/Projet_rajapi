from celery import shared_task
from django.conf import settings
from .models import Project
from .services import ProjectMemberService
import logging

logger = logging.getLogger(__name__)

@shared_task
def verify_all_project_members():
    """Tâche périodique qui vérifie tous les membres actifs des projets"""
    member_service = ProjectMemberService()
    results = {
        'verified': [],
        'deactivated': [],
        'errors': []
    }
    
    try:
        # Récupérer un token d'authentification service-to-service
        service_token = settings.MICROSERVICE_AUTH_TOKEN
        
        for project in Project.objects.all():
            try:
                project_results = member_service.verify_all_members(project, service_token)
                
                results['verified'].extend(project_results['verified'])
                
                if project_results['deactivated']:
                    results['deactivated'].extend(project_results['deactivated'])
                    
                    # Créer une entrée dans le journal des modifications
                    project.logs.create(
                        action='member_removed',
                        changes={'deactivated_members': project_results['deactivated']},
                        description=f"Membres désactivés automatiquement: {', '.join(project_results['deactivated'])}"
                    )
                    
            except Exception as e:
                error_msg = f"Erreur lors de la vérification du projet {project.reference_number}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                
        logger.info(f"Vérification des membres terminée: "
                   f"{len(results['verified'])} vérifiés, "
                   f"{len(results['deactivated'])} désactivés, "
                   f"{len(results['errors'])} erreurs")
                   
        return results
        
    except Exception as e:
        error_msg = f"Erreur critique lors de la vérification des membres: {str(e)}"
        logger.error(error_msg)
        raise