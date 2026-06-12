import os
import sys
import json
import django

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'placement_portal.settings')
django.setup()

from django.apps import apps

def generate_metadata():
    metadata = {}
    
    # We want to document the models in the 'portal' app
    portal_app = apps.get_app_config('portal')
    
    for model in portal_app.get_models():
        model_name = model._meta.db_table
        metadata[model_name] = {
            "model_class": model.__name__,
            "verbose_name": str(model._meta.verbose_name),
            "description": model.__doc__.strip() if model.__doc__ else "",
            "fields": {}
        }
        
        for field in model._meta.get_fields():
            if field.is_relation and not field.concrete:
                continue
                
            field_info = {
                "type": field.get_internal_type(),
                "nullable": field.null,
                "blank": field.blank,
            }
            
            # Add help text if present
            if hasattr(field, 'help_text') and field.help_text:
                field_info["help_text"] = str(field.help_text)
                
            # Add choices if present
            if field.choices:
                field_info["choices"] = {val: label for val, label in field.choices}
                
            # Add foreign key target table if applicable
            if field.is_relation and field.related_model:
                field_info["related_table"] = field.related_model._meta.db_table
                
            metadata[model_name]["fields"][field.name] = field_info
            
    # Write to portal/metadata.json
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'portal', 'metadata.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"Metadata written successfully to {output_path}")

if __name__ == '__main__':
    generate_metadata()
