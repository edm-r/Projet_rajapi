# 📚 Documentation API - Gestion de Projets

## 📝 Introduction
Cette API permet de gérer des projets, des documents associés et des tâches. Elle repose sur Django Rest Framework et inclut des fonctionnalités avancées comme l'authentification des membres, la journalisation des modifications et la gestion des autorisations.

---

## 📂 Structure de l'API

### 1⃣ **Gestion des Projets (`project_views.py`)**
Ce module gère les projets et leurs membres.

#### 🔹 **Endpoints disponibles :**
| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/projects/` | Liste tous les projets accessibles à l'utilisateur |
| `POST` | `/projects/` | Crée un nouveau projet |
| `GET` | `/projects/{id}/` | Récupère les détails d'un projet |
| `PUT/PATCH` | `/projects/{id}/` | Met à jour un projet |
| `DELETE` | `/projects/{id}/` | Supprime un projet |
| `POST` | `/projects/{id}/add_member/` | Ajoute un membre au projet |
| `DELETE` | `/projects/{id}/remove_member/?email=` | Supprime un membre |
| `GET` | `/projects/{id}/members/` | Liste les membres d’un projet |
| `GET` | `/projects/{id}/versions/` | Liste l’historique des modifications |
| `POST` | `/projects/{id}/restore_version/` | Restaure une version précédente |

#### 🔹 **Sécurité & Authentification**
- Seuls les utilisateurs authentifiés (`IsAuthenticated`) peuvent accéder aux projets.
- Certains endpoints nécessitent des rôles spécifiques (`IsProjectOwner`, `IsProjectMember`).
- Vérification des membres via un microservice d'authentification.

---

### 2⃣ **Gestion des Documents (`document_views.py`)**
Ce module gère les documents liés aux projets.

#### 🔹 **Endpoints disponibles :**
| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/projects/{id}/documents/` | Liste des documents d'un projet |
| `POST` | `/projects/{id}/documents/` | Ajoute un document |
| `PUT/PATCH` | `/projects/{id}/documents/{doc_id}/` | Met à jour un document |
| `DELETE` | `/projects/{id}/documents/{doc_id}/` | Supprime un document |

#### 🔹 **Journalisation des Modifications**
Chaque action est enregistrée dans le `ProjectChangeLog` :
- 📌 `document_added` : Ajout d'un document
- 📝 `document_updated` : Modification d'un document
- ❌ `document_removed` : Suppression d'un document

---

### 3⃣ **Gestion des Tâches (`task_views.py`)**
Ce module permet la gestion des tâches dans un projet.

#### 🔹 **Endpoints disponibles :**
| Méthode | URL | Description |
|---------|-----|-------------|
| `GET` | `/projects/{id}/tasks/` | Liste des tâches d'un projet |
| `POST` | `/projects/{id}/tasks/` | Ajoute une tâche |
| `PUT/PATCH` | `/projects/{id}/tasks/{task_id}/` | Met à jour une tâche |
| `DELETE` | `/projects/{id}/tasks/{task_id}/` | Supprime une tâche |

---

## 🔐 Sécurité et Authentification (`authentication.py`)
L'API utilise un microservice pour l'authentification (`MicroserviceTokenAuthentication`).
- **Vérification du token** avec l'endpoint suivant :
  `https://rajapi-cop-auth-api-33be22136f5e.herokuapp.com/auth/`
- **Création automatique des utilisateurs** si non existants

---

## 🛠 Exemples de Tests API
### Test avec `curl`
```bash
curl -X GET "http://127.0.0.1:8000/projects/" -H "Authorization: Bearer your_token"
```

### Test avec Postman
1. Ouvre Postman
2. Crée une nouvelle requête `GET`
3. URL : `http://127.0.0.1:8000/projects/`
4. Ajoute l'en-tête :
   - `Authorization`: `Bearer your_token`
5. Exécute la requête et vérifie la réponse.

---

## 💚 Licence
Cette API est sous licence **MIT**.

---

