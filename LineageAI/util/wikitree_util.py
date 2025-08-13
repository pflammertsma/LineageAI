"""
wikitree_api.py

A simple Python interface for the WikiTree API using requests.
See: https://github.com/wikitree/wikitree-api
"""

from LineageAI.api.wikitree_api import get_relatives


FIELDS = ["Name",
          "BirthDate", "BirthLocation", "DeathDate", "DeathLocation",
          "FirstName", "MiddleName", "LastNameAtBirth", "LastNameCurrent", 
          "Bio", "bio"]


def get_profile(profile_id: str):
    """
    Get a well-rounded profile for a person using the WikiTree API, including their basic info,
    full biography and details about their parents, siblings, spouses and children.

    Args:
        WikiTree profile ID
    Returns:
        dict: Profile data or an error dictionary if input is invalid.
    """
    # Start by invoking get_relatives and requesting the required information
    data = get_relatives({"Name": profile_id, "fields": [
            "Name", "Id", 
            "BirthDate", "BirthLocation", "DeathDate", "DeathLocation",
            "FirstName", "MiddleName", "LastNameAtBirth", "LastNameCurrent", 
            "Bio"
        ]})

    # Quick validation
    if data.get('status') != 'ok':
        return data
    if 'person' not in data:
        return {"status": "error", "message": f"Invalid data from API: {data}"}

    # Make a deep copy to avoid modifying the original input
    person_data = data['person'].copy()
    # This will be the new, transformed person object
    new_person = {}

    # --- Basic Information ---
    # Copy essential fields from the main person, including Gender
    for key in FIELDS:
        if key in person_data:
            new_person[key] = person_data[key]

    # --- Parents ---
    # Replace Father and Mother IDs with their respective data objects
    if 'Parents' in person_data and isinstance(person_data['Parents'], dict):
        parents_info = person_data['Parents']
        father_id = str(person_data.get('Father'))
        mother_id = str(person_data.get('Mother'))

        if father_id in parents_info:
            new_father = {}
            father_data = parents_info[father_id]
            for key in FIELDS:
                if key in father_data:
                    new_father[key] = father_data[key]
            new_person['Father'] = new_father

        if mother_id in parents_info:
            new_mother = {}
            mother_data = parents_info[mother_id]
            for key in FIELDS:
                if key in mother_data:
                    new_mother[key] = mother_data[key]
            new_person['Mother'] = new_mother

    # --- Spouses ---
    # Convert the Spouses dictionary to a list of spouse objects
    spouse_id_to_name = {}
    if 'Spouses' in person_data and isinstance(person_data['Spouses'], dict):
        new_person['Spouses'] = []
        for spouse_id, spouse_data in person_data['Spouses'].items():
            # Store spouse name for later use in Children processing
            if 'Name' in spouse_data:
                spouse_id_to_name[spouse_id] = spouse_data['Name']
            new_spouse = {}
            for key in FIELDS:
                if key in spouse_data:
                    new_spouse[key] = spouse_data[key]
            new_person['Spouses'].append(new_spouse)

    # --- Children ---
    # Convert the Children dictionary to a list, replacing parent IDs with names
    # based on the main person's gender.
    if 'Children' in person_data and isinstance(person_data['Children'], dict):
        new_person['Children'] = []
        main_person_name = person_data.get('Name')
        main_person_gender = person_data.get('Gender')

        for child_data in person_data['Children'].values():
            new_child = {}
            for key in FIELDS:
                if key in child_data:
                    new_child[key] = child_data[key]
            
            if main_person_gender == 'Male':
                new_child['Father'] = main_person_name
                # The mother is the other parent, found via the spouse map
                new_child['Mother'] = spouse_id_to_name.get(str(child_data.get('Mother')))
            elif main_person_gender == 'Female':
                new_child['Mother'] = main_person_name
                # The father is the other parent, found via the spouse map
                new_child['Father'] = spouse_id_to_name.get(str(child_data.get('Father')))
            else: # Fallback if gender is not specified
                new_child['Father'] = "Unknown"
                new_child['Mother'] = "Unknown"

            new_person['Children'].append(new_child)

    # --- Siblings ---
    # Convert the Siblings dictionary to a list of simplified sibling objects
    if 'Siblings' in person_data and isinstance(person_data['Siblings'], dict):
        new_person['Siblings'] = []
        for sibling_data in person_data['Siblings'].values():
            new_sibling = {}
            for key in FIELDS:
                if key in sibling_data:
                    new_sibling[key] = sibling_data[key]
            new_person['Siblings'].append(new_sibling)

    return {'status': 'ok', 'person': new_person}
