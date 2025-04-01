import requests
from django.conf import settings
from datetime import datetime
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.base_url = getattr(settings, 'URL_B')
        
    def get_user_profile(self, email, auth_token):
        """Récupère le profil complet de l'utilisateur avec vérification d'email"""
        cache_key = f"user_profile_{email}"
        cached = cache.get(cache_key)
        
        if cached:
            logger.info(f"Using cached profile for {email}")
            return cached
            
        try:
            logger.info(f"Fetching profile for {email} from auth service")
            
            response = requests.get(
                f"{self.base_url}/profile/",
                params={"email": email},
                headers={'Authorization': auth_token},
                timeout=10
            )
            
            logger.debug(f"Auth service response: {response.status_code} - {response.text}")
            
            if response.status_code == 404:
                raise Exception({
                    "code": "USER_NOT_FOUND",
                    "detail": "User does not exist in authentication system."
                })
                
            response.raise_for_status()
            profile = response.json()
            
            # Validation cruciale de l'email
            if profile.get('email', '').lower() != email.lower():
                logger.error(f"Email mismatch: requested {email}, got {profile.get('email')}")
                raise Exception({
                    "code": "USER_EMAIL_MISMATCH",
                    "detail": "Email does not match authentication records."
                })
                
            # Cache le profil pour 5 minutes
            cache.set(cache_key, profile, timeout=300)
            return profile
            
        except requests.RequestException as e:
            logger.error(f"Auth service request failed for {email}: {str(e)}")
            # Retourne le cache si disponible en cas d'erreur
            if cached:
                logger.warning("Returning cached profile due to auth service error")
                return cached
            raise Exception({
                "code": "AUTH_SERVICE_ERROR",
                "detail": f"Error communicating with auth service: {str(e)}"
            })

    def verify_user_exists(self, email, auth_token):
        """Vérifie seulement si l'utilisateur existe (plus léger)"""
        try:
            # Utilise le cache d'abord
            cache_key = f"user_exists_{email}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
                
            # Vérification rapide sans récupérer tout le profil
            response = requests.head(
                f"{self.base_url}/profile/",
                params={"email": email},
                headers={'Authorization': auth_token},
                timeout=5
            )
            
            exists = response.status_code == 200
            cache.set(cache_key, exists, timeout=300)
            return exists
            
        except requests.RequestException:
            # En cas d'erreur, on tente avec la méthode complète
            try:
                self.get_user_profile(email, auth_token)
                return True
            except Exception:
                return False

class ProjectMemberService:
    def __init__(self):
        self.auth_service = AuthService()

    def verify_member(self, member, auth_token):
        """Vérifie le statut d'un membre et met à jour si nécessaire"""
        try:
            exists = self.auth_service.verify_user_exists(member.user_email, auth_token)
            member.last_verified_at = datetime.now()
            
            if not exists and member.status == 'active':
                member.status = 'inactive'
                member.save()
                return False
            
            return exists
        except Exception as e:
            logger.error(f"Member verification failed for {member.user_email}: {str(e)}")
            raise Exception({
                "code": "MEMBER_VERIFICATION_ERROR",
                "detail": f"Error verifying member: {str(e)}"
            })

    def verify_all_members(self, project, auth_token):
        """Vérifie tous les membres actifs d'un projet"""
        results = {
            'verified': [],
            'deactivated': []
        }
        
        try:
            for member in project.members.filter(status='active'):
                try:
                    if self.verify_member(member, auth_token):
                        results['verified'].append(member.user_email)
                    else:
                        results['deactivated'].append(member.user_email)
                except Exception as e:
                    logger.error(f"Failed to verify member {member.user_email}: {str(e)}")
                    continue
                    
            return results
        except Exception as e:
            logger.error(f"Members verification failed: {str(e)}")
            raise Exception({
                "code": "MEMBERS_VERIFICATION_ERROR",
                "detail": f"Error verifying project members: {str(e)}"
            })