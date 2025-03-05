# 📌 Documentation API - Gestion de Projets

## 🔐 Authentification
L'authentification est gérée via un microservice accessible à l'URL :
```
https://rajapi-cop-auth-api.onrender.com/auth/token/
```
L'API utilise un système d'authentification basé sur des tokens (`Bearer Token`).

### 🔹 Connexion
**URL:** `/auth/login/`  
**Méthode:** `POST`

#### Exemple de requête :
```bash
curl -X POST https://rajapi-cop-auth-api.onrender.com/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
```
#### Réponse :
```json
{
  "token": "jwt_token_here",
  "user": {
    "email": "user@example.com",
    "username": "user123"
  }
}
```

---

## 🏗 Gestion des Projets
L'API permet de gérer des projets, incluant les tâches et documents associés.

### 🔹 Lister les projets
**URL:** `http://localhost:8000/api/projects/`  
**Méthode:** `GET`  
**Headers:**
- `Authorization: Bearer <TOKEN>`

#### Exemple de requête :
```bash
curl -X GET http://localhost:8000/api/projects/ \
     -H "Authorization: Bearer YOUR_TOKEN"
```
#### Réponse :
```json
[
  {
    "id": 1,
    "reference_number": "RJPC-2024-12345",
    "title": "Projet Alpha",
    "description": "Description du projet",
    "status": "in_progress",
    "owner": "user@example.com"
  }
]
```

### 🔹 Créer un projet
**URL:** `http://localhost:8000/api/projects/`  
**Méthode:** `POST`

#### Exemple de requête :
```bash
curl -X POST  http://localhost:8000/api/projects/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
          "title": "Projet Innovation Technologique",
          "description": "Développement d'une solution innovante",
          "objectives": "Créer une application révolutionnaire",
          "start_date": "2024-03-01",
          "deadline": "2024-12-31",
          "location": "Yaounde, cameroun",
          "status": "in_progress"
     }'
```

#### Réponse :
```json
{
  "id": 2,
  "reference_number": "RJPC-2024-67890",
  "title": "Nouveau Projet",
  "status": "in_progress"
}
```

---

## ✅ Gestion des Tâches
Les tâches sont associées à un projet.

### 🔹 Créer une tâche
**URL:** `http://localhost:8000/api/projects/{project_id}/tasks/`  
**Méthode:** `POST`

#### Exemple de requête :
```bash
curl -X POST http://localhost:8000/api/projects/1/tasks/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
        "title": "Nouvelle tâche",
        "description": "Détails de la tâche",
        "assigned_to": "user@example.com",
        "due_date": "2024-11-30",
        "status": "open"
     }'
```

---

## 👥 Gestion des Membres
L'API permet d'ajouter, supprimer et vérifier les membres d'un projet.

### 🔹 Ajouter un membre
**URL:** `http://localhost:8000/api/projects/{project_id}/add_member/`  
**Méthode:** `POST`

#### Exemple de requête :
```bash
curl -X POST http://localhost:8000/api/projects/1/add_member/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
        "user_email": "collaborator@example.com",
        "role": "collaborator"
     }'
```

### 🔹 Supprimer un membre
**URL:** `http://localhost:8000/api/projects/{project_id}/remove_member/?email={user_email}`  
**Méthode:** `DELETE`

#### Exemple de requête :
```bash
curl -X DELETE "http://localhost:8000/api/projects/1/remove_member/?email=collaborator@example.com" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### 🔹 Lister les membres d'un projet
**URL:** `http://localhost:8000/api/projects/{project_id}/members/`  
**Méthode:** `GET`

#### Exemple de requête :
```bash
curl -X GET http://localhost:8000/api/projects/1/members/ \
     -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📄 Gestion des Documents
Les documents peuvent être ajoutés à un projet.

### 🔹 Uploader un document
**URL:** `http://localhost:8000/api/projects/{project_id}/documents/`  
**Méthode:** `POST`  
**Headers:**
- `Authorization: Bearer <TOKEN>`
- `Content-Type: multipart/form-data`

#### Exemple de requête :
```bash
curl -X POST http://localhost:8000/api/projects/1/documents/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "title=Document Test" \
     -F "document_type=pdf" \
     -F "file=@/path/to/document.pdf"
```

#### Réponse :
```json
{
  "message": "Document uploadé avec succès",
  "document": {
    "id": 1,
    "title": "Document Test",
    "document_type": "pdf"
  }
}
```

---

### Historique des Versions
```bash
curl -X GET http://localhost:8000/api/projects/{project_id}/versions/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
```

### Restaurer une Version
```bash
curl -X POST http://localhost:8000/api/projects/1/documents/ \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{
        "version": 2
     }'
```

## 📌 Conclusion
Cette documentation couvre l'ensemble des fonctionnalités de l'API, incluant l'authentification, la gestion des projets, des tâches, des documents et des membres. Pour tester l'API, utilisez des outils comme `curl`, Postman ou tout autre client API.

Pour toute question, n'hésitez pas à me contacter ! 🚀

