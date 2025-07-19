"""
wikitree_api.py

A simple Python interface for the WikiTree API using requests.
See: https://github.com/wikitree/wikitree-api

For testing, invoke:
```
from LineageAI.wikitree_api import test_api
test_api()
`
"""

import requests
import json
from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent
from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST

# TODO After testing...
AGENT_MODEL = MODEL_FAST

WIKITREE_API_URL = "https://api.wikitree.com/api.php"

def test_api():
    """
    Test the WikiTree API functions.
    """
    print("Testing WikiTree API...")

    # Example for search_people
    params = {"FirstName": "Migchiel", "LastName": "Slijt", "limit": 5, "fields": ["Name", "BirthDate"]}
    result = search_people(json.dumps(params))
    print("\nsearch_people:")
    print(result)

    # Example for get_person
    params = {"Name": "Slijt-6", "fields": ["Name", "BirthDate"]}
    result = get_person(json.dumps(params))
    print("\nget_person:")
    print(result)

    # Example for get_profile
    params = {"Name": "Slijt-6", "fields": ["Name", "BirthDate", "DeathDate", "Bio"]}
    result = get_profile(json.dumps(params))
    print("\nget_profile:")
    print(result)

    # Example for get_ancestors
    params = {"Name": "Slijt-6", "depth": 2, "fields": ["Name", "BirthDate"]}
    result = get_ancestors(json.dumps(params))
    print("\nget_ancestors:")
    print(result)

    # Example for get_descendants
    params = {"Name": "Slijt-6", "depth": 2, "fields": ["Name", "BirthDate"]}
    result = get_descendants(json.dumps(params))
    print("\nget_descendants:")
    print(result)


def search_people(json_str: str):
    """
    Search for people using the WikiTree searchPerson API action.
    Args:
        json_str (str): JSON string with search parameters. Supported keys: FirstName, LastName, BirthYear, DeathYear, limit, fields
    Returns:
        dict: Search results or error message
    """
    try:
        params = json.loads(json_str)
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
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
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


def get_person(json_str: str):
    """
    Get a person's profile by WikiTree ID.
    Args:
        json_str (str): JSON string with parameters. Supported keys: Name, fields, resolveRedirect
    Returns:
        dict: Person profile data or error message
    """
    try:
        params = json.loads(json_str)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'Name' in params:
        params['key'] = params.pop('Name')    
    params['action'] = 'getPerson'
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting person: {params}")
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
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


def get_profile(json_str: str):
    """
    Get a profile using the WikiTree getProfile API action.
    Args:
        json_str (str): JSON string with parameters. Supported keys: User_Id, fields, bioFormat, resolveRedirect, etc.
    Returns:
        dict: Profile data or error message
    """
    try:
        params = json.loads(json_str)
        if not isinstance(params, dict):
            return {'status': 'error', 'error_message': 'JSON must represent an object with parameters.'}
    except Exception as e:
        return {'status': 'error', 'error_message': f'Invalid JSON: {str(e)}'}
    # Replace `Name` key with `key`
    if 'User_Id' in params:
        params['key'] = params.pop('Name')    
    params['action'] = 'getProfile'
    # Convert fields list to comma-separated string if present
    if 'fields' in params and isinstance(params['fields'], list):
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting profile: {params}")
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
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


def get_ancestors(json_str: str):
    """
    Get ancestors for a person using the WikiTree getAncestors API action.
    Args:
        json_str (str): JSON string with parameters. Supported keys: Name, depth, fields, etc.
    Returns:
        dict: Ancestors data or error message
    """
    try:
        params = json.loads(json_str)
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
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        # Handle both dict and list responses
        if isinstance(data, dict):
            return {'status': 'ok', 'ancestors': data.get('ancestors', data)}
        elif isinstance(data, list):
            return {'status': 'ok', 'ancestors': data}
        else:
            return {'status': 'ok', 'ancestors': data}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}

def get_descendants(json_str: str):
    """
    Get descendants for a person using the WikiTree getDescendants API action.
    Args:
        json_str (str): JSON string with parameters. Supported keys: Name, depth, fields, etc.
    Returns:
        dict: Descendants data or error message
    """
    try:
        params = json.loads(json_str)
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
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        # Handle both dict and list responses
        if isinstance(data, dict):
            return {'status': 'ok', 'descendants': data.get('descendants', data)}
        elif isinstance(data, list):
            return {'status': 'ok', 'descendants': data}
        else:
            return {'status': 'ok', 'descendants': data}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


wikitree_api_agent = LlmAgent(
    name="WikiTreeAgent",
    model=AGENT_MODEL,
    description="""
    Agent to query for existing WikiTree profiles.
    """,
    instruction="""
    You are an agent capable of querying the WikiTree API to retrieve existing, albeit incomplete,
    genealogical profiles.

    These are all the known fields for requests and responses in the WikiTree API:

    | Field                   | Description                                                       |
    |-------------------------|-------------------------------------------------------------------|
    | Name                    | The WikiTree ID, with spaces replaced by underscores as in an URL |
    | FirstName               | First Name                                                        |
    | MiddleName              | Middle Name                                                       |
    | MiddleInitial           | First letter of Middle Name                                       |
    | LastNameAtBirth         | Last name at birth, used for WikiTree ID                          |
    | LastNameCurrent         | Current last name                                                 |
    | Nicknames               | Nicknames                                                         |
    | LastNameOther           | Other last names                                                  |
    | RealName                | The "Preferred" first name of the profile                         |
    | Prefix                  | Prefix                                                            |
    | Suffix                  | Suffix                                                            |
    | BirthDate               | The date of birth, YYYY-MM-DD. Month and Day may be zeros.        |
    | DeathDate               | The date of death, YYYY-MM-DD. Month and Day may be zeros.        |
    | BirthLocation           | Birth location                                                    |
    | DeathLocation           | Death location                                                    |
    | BirthDateDecade         | Date of birth rounded to a decade, e.g. 1960s                     |
    | DeathDateDecade         | Date of death rounded to a decade, e.g. 1960s                     |
    | Gender                  | Male or Female                                                    |
    | IsLiving                | 1 if the person is considered "living", 0 otherwise               |
    | Father                  | The `User_Id` of the father. 0 if empty. Null if private.         |
    | Mother                  | The `User_Id` of the mother. 0 if empty. Null if private.         |
    | HasChildren             | 1 if the profile has at least one child                           |
    | NoChildren              | 1 if the "No more children" box is checked                        |
    | IsRedirect              | 1 if the profile is a redirection to another profile              |
    | DataStatus              | Array of "guess", "certain", etc. flags for the data fields.      |
    | PhotoData               | Detailed info for the primary photo. Implies the Photo field.     |
    | Connected               | 1 if connected to the global family tree, 0 if unconnected        |
    | Bio                     | The biography text (not included by default, see bioFormat param) |
    | IsMember                | True/1 if the profile is an active WikiTree member, else false/0  |
    | EditCount               | The contribution count of the user/profile.                       |

    Whenever querying the WikiTree API, you must include the list of fields you want to retrieve.
    For example, to retrieve the WikiTree ID, and basic information about a person, you would
    include these fields:
        fields: ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"]

    You must always use `Name` to reference profiles. These are the WikiTree IDs, for example:
        `Slijt-6` for the profile https://www.wikitree.com/wiki/Slijt-6

    The most relevant fields for genealogical profiles are:
        - Name (this is the WikiTree ID)
        - FirstName
        - LastNameAtBirth
        - Gender
        - BirthDate, noting that Month and Day may be zeros if they are unknown
        - DeathDate, noting that Month and Day may be zeros if they are unknown

    You might drill down into the profile to retrieve more information, such as:
        - Mother: The WikiTree ID of the mother, if known
        - Father: The WikiTree ID of the father, if known

    The following functions are available to you:
    - `search_people`: Search for people in order to find the WikiTree IDs for profiles.
    - `get_profile`: Retrieve a profile by WikiTree ID.
    - `get_ancestors`: Retrieve the ancestors of a profile by WikiTree ID.
    - `get_descendants`: Retrieve the descendants of a profile by WikiTree ID.

    All functions must be invoked with a JSON string.

    SEARCHING FOR PEOPLE
    --------------------

    Invoke `search_people` with a JSON string containing keys matching the following parameters:
    - Search parameters within any number of the following fields:
        - `FirstName`: First Name
        - `LastName`: Last Name
        - `BirthDate`: Birth Date (YYYY-MM-DD)
        - `DeathDate`: Death Date (YYYY-MM-DD)
        - `RealName`: Real/Preferred Name
        - `LastNameCurrent`: Current Last Name
        - `BirthLocation`: Birth Location
        - `DeathLocation`: Death Location
        - `Gender`: Gender (Male, Female)
        - `fatherFirstName`: Father's First Name
        - `fatherLastName`: Father's Last Name
        - `motherFirstName`: Mother's First Name
        - `motherLastName`: Mother's Last Name
        - `watchlist`: 1 (restrict to watchlist)
        - `dateInclude`: both (require dates on matched profiles) or neither (include matches without dates)
        - `dateSpread`: 1-20 (spread of years for date matches)
        - `centuryTypo`: 1 (include possible century typos in date matches)
        - `isLiving`: 1 (restrict matches to profiles of living people)
        - `skipVariants`: 1 (skip variant last names in matches, only match exact surname)
        - `lastNameMatch`: Last Name Matching (all, current, birth, strict)
        - `sort`: Sort Order [first, last, birth, death, manager]
        - `secondarySort`: Secondary Sort Order [first, last, birth, death, manager]
        - `limit`: Number of results to return (1-100, default 10)
        - `start`: Starting offset of return set (default 0)
        - `fields`: Comma-delimited list of profile data fields to retrieve.
    - `limit`: The maximum number of results to return (default is 10, max is 100)
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is not supported for this function.

    Here's an example of how to invoke `search_people` to search for "Migchiel Slijt":
    {
        "FirstName": "Migchiel",
        "LastName": "Slijt",
        "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"]
    }
    The function will return a list of matches for the search criteria:
    { 'status': 'ok', 
      'results': [{...
        'matches': [
          {"Name":"Slijt-6","FirstName":"Migchiel","LastNameAtBirth":"Slijt","BirthDate":"1842-03-28","DeathDate":"1872-12-29","index":0},
          ... ]
        ... } ],
      ... }

    This `search_people` function helps us find whether a WikiTree profile already exists, and if
    so, what its WikiTree ID is.

    GETTING A PERSON
    ----------------

    Take special note of the `User_Id` property that is ONLY returned for `Father` and `Mother`.
    To retrieve the WikiTree ID of a profile's parents, you must use the `User_Id` property by
    querying the `get_person` function by provinding `User_Id` as the `User_Id` parameter. You
    cannot use `get_profile` for this purpose. This is the only time you should use the `User_Id`
    or `get_person`.

    If you already know the WikiTree ID of a profile, there is no need to execute `get_person`.

    Then, and only then, invoke `get_person` with a JSON string containing keys matching the
    following parameters:
    - `User_Id`: The `User_Id` of the profile you want to retrieve (this is a number and is NOT the
      same as a WikiTree ID, which is alphanumeric).
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is supported for this function and returns the biography text in WikiTree
        format.

    GETTING A PROFILE
    -----------------

    Invoke `get_profile` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve (e.g., "Slijt-6"). This MUST be
      the WikiTree ID, not the `User_Id`. Providing a number will return an unexpected result!
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
      field `Bio` is supported for this function and returns the biography text in WikiTree format.

    Here's an example of a request to retrieve the contents of profile:
    {
        "Name": "Slijt-6",
        "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate", "Bio"]
    }
    The function will return a profile object with the requested fields:
    { 'status': 'ok', 'profile': [{'page_name': 'Slijt-6', 'profile': {'Name': 'Slijt-6', 'BirthDate': ... }, 'status': 0 } ]}

    This `get_profile` function is the essential function to retrieve the entire content of a
    WikiTree profile, including the biography.

    You must always request the `Bio` field, as it contains the content of the current biography.
    Requesting the `Bio` field will provide additional information that is not contained in the
    individual fields and is therefore the most useful part of  retrieving a biography.

    FINDING ANCESTORS
    -----------------

    Invoke `get_ancestors` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve ancestors for (e.g., "Slijt-6").
    - `depth`: The number of generations to retrieve (default is 2).
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is supported for this function and returns the biography text in WikiTree
        format.

    Here's an example of a request to retrieve the ancestors of a profile:
    {
        "Name": "Slijt-6",
        "depth": 2,
        "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"]
    }
    The function will return a list of ancestors for the specified profile:
    [ { "user_name": "Slijt-6",
        "ancestors": [
          {"Name":"Slijt-6", 'FirstName': 'Migchiel', 'LastNameAtBirth': 'Slijt', 'BirthDate': '1842-03-28', 'DeathDate': '1872-12-29'},
          ... ]
        ... } ]

    This `get_ancestors` function retrieves the ancestors of a profile, allowing you to explore
    the family tree and lineage of a person. If you don't know the WikiTree ID of the ancestors,
    this function can help you find them.
    
    If you are asked to find parents of a profile, you must use the `get_ancestors`.

    FINDING DESCENDANTS
    -------------------

    The `get_descendants` function if functionally identical to `get_ancestors`, but retrieves the
    descendants of a profile.  If you don't know the WikiTree ID of the descendants, this function
    can help you find them.

    If you are asked to find children of a profile, you must use the `get_descendants`.

    UPDATING A BIOGRAPHY
    --------------------

    You are unable to update a biography directly using the WikiTree API. Instead, you must
    transfer to the WikitreeFormatterAgent to format the updated biography and provide it to the
    user.

    AFTER COMPLETING YOUR TASKS
    ---------------------------

    After you have completed your tasks, you must transfer back to the LineageAiOrchestrator unless
    you are confident you have satisfied the user's request. However, if for example searched for
    a profile but couldn't find it, don't ask the user for other search criteria and instead
    immediately transfer to LineageAiOrchestrator so that research can be performed to create the
    profile.

    If you found a profile that was a very close match, but it wasn't exact match, you must provide
    a clear overview of what you found and compare it to the user's request. If you are unsure,
    transfer to the LineageAiOrchestrator for further assistance.

    ANY OTHER FUNCTIONALITY
    -----------------------

    You are not able to perform any other functionality than described above. You must transfer to
    the LineageAiOrchestrator for any other tasks, such as researching, formatting or updating
    profiles.

    """,
    tools=[get_profile, get_person, search_people, get_ancestors, get_descendants],
    output_key="genealogy_records"
)
