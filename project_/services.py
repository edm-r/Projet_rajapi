import requests
from django.conf import settings
from datetime import datetime
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.base_url = settings.URL_B
        
    def get_user_profile(self, email, auth_token):
        """Récupère le profil utilisateur depuis le service d'auth"""
        try:
            response = requests.get(
                f"{self.base_url}/profile/",
                params={"email": email},
                headers={'Authorization': auth_token},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Erreur lors de la récupération du profil: {str(e)}")
            raise

    def verify_user_exists(self, email, auth_token):
        """Vérifie si un utilisateur existe dans le service d'auth"""
        try:
            response = requests.get(
                f"{self.base_url}/profile/",
                params={"email": email},
                headers={'Authorization': auth_token},
                timeout=10
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

class ProjectMemberService:
    def __init__(self):
        self.auth_service = AuthService()

    def verify_member(self, member, auth_token):
        """Vérifie le statut d'un membre et met à jour si nécessaire"""
        exists = self.auth_service.verify_user_exists(member.user_email, auth_token)
        member.last_verified_at = datetime.now()
        
        if not exists and member.status == 'active':
            member.status = 'inactive'
            member.save()
            return False
        
        return exists

    def verify_all_members(self, project, auth_token):
        """Vérifie tous les membres actifs d'un projet"""
        results = {
            'verified': [],
            'deactivated': []
        }
        
        for member in project.members.filter(status='active'):
            if self.verify_member(member, auth_token):
                results['verified'].append(member.user_email)
            else:
                results['deactivated'].append(member.user_email)
                
        return results