import requests
import json

def get_field_ids(memento_lib_id, memento_entryid, memento_token):
    """
    Retrieves the dynamic field IDs for a given Memento library.
    """
    try:
        url = f"https://api.mementodatabase.com/v1/libraries/{memento_lib_id}/entries/{memento_entryid}?token={memento_token}"
        response = requests.get(url)
        data = response.json()
        print(data)
        # Create a mapping of field names to their dynamic IDs
        field_ids = {field["name"]: field["id"] for field in data.get("fields", [])}
        return field_ids
    except Exception as e:
        print("Error retrieving field IDs:", e)
        return {}
    

get_field_ids("v9w7T6k4k", "SiNSdE15YjRXZnlyVFFTPjNkaW8", "XvXJXc5CtwCwpSG5wL0XpR9cqsuLLD")