from typing import Dict, Any

class TemplateRegistry:
    def __init__(self):
        # Phase 2 Stub: Store paths to university templates
        self.templates = {
            "air": "backend/templates_registry/templates/air",
            "bahria": "backend/templates_registry/templates/bahria",
            "nust": "backend/templates_registry/templates/nust"
        }

    def get_template(self, university: str) -> Dict[str, Any]:
        """
        Returns the template configuration for a given university.
        """
        uni_key = university.lower()
        if uni_key not in self.templates:
            raise ValueError(f"Template for university '{university}' not found.")
        
        return {
            "university": uni_key,
            "template_dir": self.templates[uni_key]
        }