from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configuration de la tâche périodique
app.conf.beat_schedule = {
    'verify-project-members': {
        'task': 'your_app.tasks.verify_all_project_members',
        'schedule': crontab(hour='0', minute='0'),  # Exécution à minuit chaque jour
    },
}