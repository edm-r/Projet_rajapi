from datetime import datetime, date
import json
from django.forms.models import model_to_dict

from project_.models import ProjectChangeLog

def json_serial(obj):
    """Fonction pour sérialiser les objets date en JSON"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} n'est pas JSON serializable")

class ChangeLogMixin:
    def _log_change(self, project, action, changes, description=None):
        """Créer une entrée dans le journal des modifications"""
        json_changes = json.loads(json.dumps(changes, default=json_serial))
        
        return ProjectChangeLog.objects.create(
            project=project,
            user=self.request.user,
            action=action,
            changes=json_changes,
            description=description
        )

    def _get_field_changes(self, old_data, new_data):
        """Identifier les changements entre deux états"""
        changes = {}
        for field, new_value in new_data.items():
            if field in old_data:
                old_value = old_data[field]
                if old_value != new_value:
                    if isinstance(old_value, (date, datetime)):
                        old_value = old_value.isoformat()
                    if isinstance(new_value, (date, datetime)):
                        new_value = new_value.isoformat()
                    changes[field] = {'from': old_value, 'to': new_value}
        return changes