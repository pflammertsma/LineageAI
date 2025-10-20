"""
wikitree_api.py

A simple Python interface for the WikiTree API using requests.
See: https://github.com/wikitree/wikitree-api
"""

from LineageAI.constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from LineageAI.util.utils import rate_limited_get
import requests
import json
from typing import Dict, Any


WIKITREE_API_URL = "https://api.wikitree.com/api.php"

def search_profiles(json_dict: Dict[str, Any]):
    """
    Search for people using the WikiTree searchPerson API action.
    Args:
        JSON dictionary with search parameters. Supported keys: FirstName, LastName, BirthYear, DeathYear, limit, fields
    Returns:
        dict: Search results or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with search parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Set required action
    params['action'] = 'searchPerson'
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    try:
        logger.debug(f"Searching people: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        # Handle both dict and list responses
        if isinstance(data, dict):
            return {'status': 'ok', 'results': data.get('results', data)}
        elif isinstance(data, list):
            return {'status': 'ok', 'results': data}
        else:
            return {'status': 'ok', 'results': data}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


def get_person(json_dict: Dict[str, Any]):
    """
    Get a person's profile by WikiTree ID.
    Args:
        JSON dictionary with parameters. Supported keys: Name, fields, resolveRedirect
    Returns:
        dict: Person profile data or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'Name' in params:
        params['key'] = params.pop('Name')    
    if 'Id' in params:
        params['key'] = params.pop('Id')    
    params['action'] = 'getPerson'
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting person: {params}")
        print(f"Requesting person: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        # Handle both dict and list responses
        if isinstance(data, dict):
            return {'status': 'ok', 'person': data.get('person', data)}
        elif isinstance(data, list):
            return {'status': 'ok', 'person': data}
        else:
            return {'status': 'ok', 'person': data}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


def get_profile(json_dict: Dict[str, Any]):
    """
    Get a profile using the WikiTree getProfile API action.
    Args:
        JSON dictionary with parameters. Supported keys: Id, fields, bioFormat, resolveRedirect, etc.
    Returns:
        dict: Profile data or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'Name' in params:
        params['key'] = params.pop('Name')    
    if 'Id' in params:
        return {'status': 'error', 'error_message': 'This function does not support searching by \'Id\'.'}
    params['action'] = 'getProfile'
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting profile: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        # Handle both dict and list responses
        if isinstance(data, dict):
            return {'status': 'ok', 'profile': data.get('profile', data)}
        elif isinstance(data, list):
            return {'status': 'ok', 'profile': data}
        else:
            return {'status': 'ok', 'profile': data}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


def get_ancestors(json_dict: Dict[str, Any]):
    """
    Get ancestors for a person using the WikiTree getAncestors API action.
    Args:
        json_dict (dict): JSON dictionary with parameters. Supported keys: Name, depth, fields, etc.
    Returns:
        dict: Ancestors data or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'Name' in params:
        params['key'] = params.pop('Name')    
    params['action'] = 'getAncestors'
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting ancestors: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        # Expecting a list with one dict
        if isinstance(data, list) and data:
            entry = data[0]
            # Error case: status is not 0 or ancestors missing
            if entry.get('status') != 0 or 'ancestors' not in entry:
                return {'status': 'error', 'error_message': entry.get('status', 'Unknown error')}
            # Remove the first ancestor (the profile itself)
            ancestors = entry['ancestors'][1:] if len(entry['ancestors']) > 1 else []
            return {'status': 'ok', 'ancestors': ancestors}
        else:
            return {'status': 'error', 'error_message': 'Unexpected API response'}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


def get_descendants(json_dict: Dict[str, Any]):
    """
    Get descendants for a person using the WikiTree getDescendants API action.
    Args:
        json_dict (dict): JSON dictionary with parameters. Supported keys: Name, depth, fields, etc.
    Returns:
        dict: Descendants data or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'Name' in params:
        params['key'] = params.pop('Name')    
    params['action'] = 'getDescendants'
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting descendants: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        # Expecting a list with one dict
        if isinstance(data, list) and data:
            entry = data[0]
            # Error case: status is not 0 or descendants missing
            if entry.get('status') != 0 or 'descendants' not in entry:
                return {'status': 'error', 'error_message': entry.get('status', 'Unknown error')}
            # Remove the first descendant (the profile itself)
            descendants = entry['descendants'][1:] if len(entry['descendants']) > 1 else []
            return {'status': 'ok', 'descendants': descendants}
        else:
            return {'status': 'error', 'error_message': 'Unexpected API response'}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


def get_relatives(json_dict: Dict[str, Any]):
    """
    Get relatives (parents, siblings, spouses) for a person using the WikiTree getRelatives API action.
    Args:
        JSON dictionary with parameters. Supported keys: Name, fields, etc.
    Returns:
        dict: Relatives data or error message
    """
    try:
        if isinstance(json_dict, dict):
            params = json_dict
        else:
            params = json.loads(json_dict)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `keys` (note: plural!)
    if 'Name' in params:
        params['keys'] = params.pop('Name')
    params['action'] = 'getRelatives'
    params['getParents'] = 1
    params['getSiblings'] = 1
    params['getSpouses'] = 1
    params['getChildren'] = 1
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        if 'Id' not in params['fields']:
            params['fields'].append('Id')
        if 'Name' not in params['fields']:
            params['fields'].append('Name')
        if 'Gender' not in params['fields']:
            params['fields'].append('Gender')
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting relatives: {params}")
        response = rate_limited_get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if isinstance(data, dict) and 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        if len(data) > 0:
            if 'items' in data[0] and isinstance(data[0]['items'], list) and len(data[0]['items']) > 0:
                if 'person' in data[0]['items'][0]:
                    entry = data[0]['items'][0]
                    entry['person']['UserId'] = entry['user_id']
                    return {'status': 'ok', 'person': entry['person']}
                else:
                    return {'status': 'error', 'error_message': 'No `items[0].person` object returned from API'}
            else:
                return {'status': 'error', 'error_message': '`items` is missing or not a non-empty list in API response'}
        else:
            return {'status': 'error', 'error_message': 'Empty array returned from API'}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}
