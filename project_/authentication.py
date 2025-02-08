import requests
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

class MicroserviceTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Récupérer le token depuis l'en-tête Authorization
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            # Extraire le token (en enlevant 'Bearer ')
            token = auth_header.split(' ')[1]
        except IndexError:
            return None

        # Endpoint de vérification du token
        verify_url = 'https://rajapi-cop-auth-api-33be22136f5e.herokuapp.com/auth/token/verify'
        
        try:
            # Envoyer une requête de vérification
            response = requests.post(verify_url, json={'token': token})
            response_data = response.json()
            
            # Vérifier si la réponse est valide
            if response.status_code != 200 or not response_data.get("token_valid", False):
                raise AuthenticationFailed('Token invalide ou expiré')
            
            # Récupérer les informations utilisateur de la réponse
            user_data = response_data.get('user_profile', {})

            # Récupérer ou créer l'utilisateur
            try:
                user = User.objects.get(email=user_data.get('email'))
            except User.DoesNotExist:
                # Créer un utilisateur avec un username unique
                user = User.objects.create(
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    first_name=user_data.get('first_name', ''),
                    last_name=user_data.get('last_name', '')
                )
            
            return (user, token)
        
        except requests.RequestException:
            raise AuthenticationFailed('Impossible de vérifier le token')

    def authenticate_header(self, request):
        return 'Bearer'
