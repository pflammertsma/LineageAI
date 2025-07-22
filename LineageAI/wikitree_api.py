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

from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
import requests
import json
from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent

# TODO After testing...
AGENT_MODEL = MODEL_FAST

WIKITREE_API_URL = "https://api.wikitree.com/api.php"


def search_profiles(json_str: str):
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
        print(f"Requesting person: {params}")
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
        json_str (str): JSON string with parameters. Supported keys: Id, fields, bioFormat, resolveRedirect, etc.
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
    if 'Name' in params:
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


def get_relatives(json_str: str):
    """
    Get relatives (parents, siblings, spouses) for a person using the WikiTree getRelatives API action.
    Args:
        json_str (str): JSON string with parameters. Supported keys: Name, fields, etc.
    Returns:
        dict: Relatives data or error message
    """
    try:
        params = json.loads(json_str)
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
        params['fields'] = ','.join(params['fields'])
    # Set defaults if not provided
    params.setdefault('bioFormat', 'wiki')
    params.setdefault('resolveRedirect', 1)
    try:
        logger.debug(f"Requesting relatives: {params}")
        response = requests.get(WIKITREE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response: {data}")
        if isinstance(data, dict) and 'error' in data:
            return {'status': 'error', 'error_message': data['error']}
        if len(data) > 0:
            if 'items' in data[0] and len(data[0]['items']) > 0:
                if 'person' in data[0]['items'][0]:
                    entry = data[0]['items'][0]
                    entry['person']['UserId'] = entry['user_id']
                    return {'status': 'ok', 'person': entry['person']}
                else:
                    return {'status': 'error', 'error_message': 'No `items[0].person` object returned from API'}
            else:
                return {'status': 'error', 'error_message': 'Empty `items` object returned from API'}
        else:
            return {'status': 'error', 'error_message': 'Empty array returned from API'}
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {'status': 'error', 'error_message': str(e)}


wikitree_query_agent = LlmAgent(
    name="WikiTreeProfileAgent",
    model=AGENT_MODEL,
    description="""
    You are the WikiTree Agent specializing in querying the WikiTree API to retrieve existing,
    albeit incomplete, genealogical profiles and understanding which data already exists on
    WikiTree, before transferring to the LineageAiOrchestrator for further research.
    """,
    instruction="""
    Before doing anything, you must ensure that you have some basic information about the profile
    you were asked to find. You must therefore first invoke the `get_profile` function to fetch
    basic information about the person.

    For example, if you are simply provided with the WikiTree ID "Slijt-6", you must use the
    `get_profile` function as follows:

        get_profile({"Name": "Slijt-6", "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate", "Father", "Mother", "Bio"]})

    You will not even be able to understand what a person's name is without this information.
    
    These are all the known fields for requests and responses in the WikiTree API:

    | Field                   | Description                                                       |
    |-------------------------|-------------------------------------------------------------------|
    | Id                      | The user ID, which is a numeric identifier                        |
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
    | Father                  | The `Id` of the father. 0 if empty. Null if private.              |
    | Mother                  | The `Id` of the mother. 0 if empty. Null if private.              |
    | HasChildren             | 1 if the profile has at least one child                           |
    | NoChildren              | 1 if the "No more children" box is checked                        |
    | IsRedirect              | 1 if the profile is a redirection to another profile              |
    | DataStatus              | Array of "guess", "certain", etc. flags for the data fields.      |
    | PhotoData               | Detailed info for the primary photo. Implies the Photo field.     |
    | Connected               | 1 if connected to the global family tree, 0 if unconnected        |
    | Bio                     | The biography text (not included by default, see bioFormat param) |
    | IsMember                | True/1 if the profile is an active WikiTree member, else false/0  |
    | EditCount               | The contribution count of the user/profile.                       |

    Take careful note that `Id` is a numeric identifier used between records, whereas `Name` is the
    WikiTree ID, which is alphanumeric and used primarily for URLs.

    Whenever querying the WikiTree API, you must include the list of fields you want to retrieve.
    For example, to retrieve the WikiTree ID, and basic information about a person, you would
    include these fields:
        fields: ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"]

    You must always prefer using `Name` to reference profiles. These are the WikiTree IDs. For
    example, `Slijt-6` is the WikiTree ID profile in the URL https://www.wikitree.com/wiki/Slijt-6.

    The most relevant fields for genealogical profiles are:
    - Name (this is the WikiTree ID)
    - FirstName
    - LastNameAtBirth
    - Gender
    - BirthDate
    - DeathDate
    - Mother
    - Father
    - Bio

    Note: In dates, month and day may be zeros if they are unknown. For example, 1842-03-00 means
    "March, 1842" where the exact date is unknown.

    The following functions are available to you:
    - `search_profiles`: Search for profiles in order to find their WikiTree IDs.
    - `get_person`: Resolve the WikiTree ID (`Name`) of a profile by its `Id`.
    - `get_profile`: Retrieve a profile by WikiTree ID (`Name`).
    - `get_ancestors`: Retrieve the ancestors of a profile.
    - `get_descendants`: Retrieve the descendants of a profile.

    All functions must be invoked with a JSON string.

    PERFORMING RESEARCH
    -------------------

    You cannot perform any genealogical research and must always transfer to the
    LineageAiOrchestrator to do so.

    SEARCHING FOR PROFILES
    ----------------------

    Invoke `search_profiles` with a JSON string containing keys matching the following parameters:
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

    Here's an example of how to invoke `search_profiles` to search for a profile for "Migchiel Slijt":
    ```
    {
        "FirstName": "Migchiel",
        "LastName": "Slijt",
        "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"]
    }
    ```
    The function will return a list of matches for the search criteria:
    ```
    { 'status': 'ok', 
      'results': [{...
        'matches': [
          {"Name":"Slijt-6","FirstName":"Migchiel","LastNameAtBirth":"Slijt","BirthDate":"1842-03-28","DeathDate":"1872-12-29","index":0},
          ... ]
        ... } ],
      ... }
    ```

    This `search_profiles` function helps us find whether a WikiTree profile already exists, and if
    so, what its WikiTree ID is.

    You must always transfer to the LineageAiOrchestrator before concluding your interaction with
    the user.

    GETTING A PERSON
    ----------------

    To retrieve an unknown WikiTree ID (`Name`) that corresponds with the `Id` of a profile, you
    must provide the `Id` property when querying the `get_person` function. You cannot use
    `get_profile` for this purpose. This is the only time you should use the `get_person`.

    If you already know the WikiTree ID of a profile, there is no need to execute `get_person`.

    Then, and only then, invoke `get_person` with a JSON string containing keys matching the
    following parameters:
    - `Id`: The `Id` of the profile you want to retrieve (this is a number and is NOT the same as
      a WikiTree ID (`Name`), which is alphanumeric).
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
      field `Bio` is supported for this function and returns the biography text in WikiTree
      format.

    You must always transfer to the LineageAiOrchestrator before concluding your interaction with
    the user.

    GETTING A PROFILE
    -----------------

    Invoke `get_profile` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve (e.g., "Slijt-6"). This MUST be
      the WikiTree ID, not the `Id`. Providing a number will return an unexpected result!
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
      field `Bio` is supported for this function and returns the biography text in WikiTree format.

    Here's an example of a request to retrieve the contents of profile:
    ```
    {
        "Name": "Slijt-6",
        "fields": ["Name", "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate", "Bio"]
    }
    ```
    The function will return a profile object with the requested fields:
    ```
    { 'status': 'ok', 'profile': [{'page_name': 'Slijt-6', 'profile': {'Name': 'Slijt-6', 'BirthDate': ... }, 'status': 0 } ]}
    ```

    This `get_profile` function is the essential function to retrieve the entire content of a
    WikiTree profile, including the biography.

    You must always request the `Bio` field, as it contains the content of the current biography.
    Requesting the `Bio` field will provide additional information that is not contained in the
    individual fields and is therefore the most useful part of  retrieving a biography.

    After retrieving the profile, you must immediately continue with a next step with the goal of
    performing additional research:
    1. Perform more queries to WikiTree to understand which information is already available, such
        as ancestors and descendants, or obtaining the profiles of known family members.
    2. If the profile is incomplete, you must transfer to the LineageAiOrchestrator to ask it to
        look for archival records, historical documents, or other sources outside of WikiTree.

    You must always transfer to the LineageAiOrchestrator before concluding your interaction with
    the user.

    FINDING RELATIVES
    -----------------

    Invoke `get_relatives` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve relatives for (e.g., "Slijt-6").
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is supported for this function and returns the biography text in WikiTree
        format.

    Here's an example of a request to retrieve the relatives of a profile:
    ```
    {
        "Name": "Slijt-6",
        "fields": ["Name", "BirthDate", "DeathDate"]
    ```
    }
    The function will return a the currently known parents, spouses, children and siblings of a
    specified profile:
    ```
    { "status":"ok", "person":{
        "Name":"Slijt-6",
        "BirthDate":"1842-03-28",
        "DeathDate":"1872-12-29",
        "Father":9674061,
        "Mother":9674069,
        "Parents":{ ... },
        "Spouses":{ ... },
        "Children":{
            "47228014":{
                "Name":"Slijt-7",
                "BirthDate":"1869-01-27",
                "DeathDate":"0000-00-00",
                "Father":47227210,
                "Mother":47228956
            },  ...
        },
        "Siblings":{ ... },
        "UserId":47227210
    }
    ```

    In this example, "Slijt-7" is a child of "Slijt-6". This is a simple example; it's much more
    useful to include more fields, such as "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate"
    and "Bio".

    This function allows you to understand which relationships are already present in WikiTree, but
    this information may not be complete or accurate, so you must always transfer to the
    LineageAiOrchestrator to perform research to confirm it.

    UPDATING A BIOGRAPHY
    --------------------

    You are unable to update a biography directly using the WikiTree API. Instead, you must
    transfer to the LineageAiOrchestrator.

    AFTER COMPLETING YOUR TASKS
    ---------------------------

    After you have completed your tasks, you must always transfer back to the LineageAiOrchestrator
    unless you are confident you have satisfied the user's request. It's very unlikely that you
    should stop here, however, because profiles are often incomplete and require further research.
    You mustn't ask the user for other search criteria and instead immediately transfer to
    LineageAiOrchestrator so that research can be performed to create or update a profile.

    If you found a profile that was a very close match, but it wasn't exact match, you must provide
    a clear overview of what you found and compare it to the user's request. If you are unsure,
    transfer to the LineageAiOrchestrator for further assistance.

    IMPORTANT NOTES
    ---------------

    Before transferring to the LineageAiOrchestrator, you must ensure that you have some basic
    information about the profile you were asked to find. This includes any of:
    - First and last name
    - Birth date or date range
    - Death date or date range
    - Immediate family members (parents, children, etc.)

    If you do not have any of this information, you must invoke the `get_profile` function to
    obtain it. If that fails, you should first ask the user for more information.

    If you are informed that one or more profiles have been changed, this means your data is out of
    date and you should execute any relevant functions to obtain the latest versions.

    You are not able to perform any other functionality than described above. You must transfer to
    the LineageAiOrchestrator for any other tasks, such as researching, formatting or updating
    profiles.
    """,
    tools=[get_profile, get_person, search_profiles, get_relatives],
    output_key="wikitree_profile"
)


wikitree_ancestors_agent = LlmAgent(
    name="WikiTreeAncestorsAgent",
    model=AGENT_MODEL,
    description="""
    You are the WikiTree Agent specializing in exploring any known ancestor profiles of an existing
    profile.
    """,
    instruction="""
    Invoke `get_ancestors` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve ancestors for (e.g., "Slijt-6").
    - `depth`: The number of generations to retrieve (default is 2).
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is supported for this function and returns the biography text in WikiTree
        format.

    Here's an example of a request to retrieve the ancestors of a profile:
    ```
    {
        "Name": "Slijt-6",
        "depth": 1,
        "fields": ["Id", "Name", "Mother", "Father"]
    ```
    }
    The function will return a list of ancestors for the specified profile:
    ```
    {"status":"ok","ancestors":[
      {"Id":9674061,"Name":"Slijt-2","Father":46258655,"Mother":46258661},
      {"Id":9674069,"Name":"Stolte-31","Father":46258670,"Mother":46258681}],
    }
    ```

    In this example, the ancestors of the profile "Slijt-6" are "Slijt-2" and "Stolte-31". This is
    a simple example; it's much more useful to include more fields, such as "FirstName",
    "LastNameAtBirth", "BirthDate", "DeathDate" and "Bio".

    This `get_ancestors` function retrieves the ancestors of a profile, allowing you to explore
    the family tree and lineage of a person. If you don't know the WikiTree ID of the ancestors,
    this function can help you find them.

    This function allows you to understand which ancestors are already present in WikiTree, but
    this information may not be complete or accurate, so you must always transfer to the
    LineageAiOrchestrator to perform research to confirm it.

    You are not able to perform any other functionality than described above. You must transfer to
    the LineageAiOrchestrator for any other tasks, such as researching, formatting or updating
    profiles.
    """,
    tools=[get_ancestors],
    output_key="wikitree_ancestors"
)


wikitree_descendants_agent = LlmAgent(
    name="WikiTreeDescendantsAgent",
    model=AGENT_MODEL,
    description="""
    You are the WikiTree Agent specializing in exploring any known descendant profiles of an
    existing profile.
    """,
    instruction="""
    Invoke `get_descendants` with a JSON string containing keys matching the following parameters:
    - `Name`: The WikiTree ID of the profile you want to retrieve ancestors for (e.g., "Slijt-6").
    - `depth`: The number of generations to retrieve (default is 2).
    - `fields`: A list of fields that you want to retrieve from the API from the table above. The
        field `Bio` is supported for this function and returns the biography text in WikiTree
        format.

    Here's an example of a request to retrieve the ancestors of a profile:
    ```
    {
        "Name": "Slijt-6",
        "depth": 2,
        "fields": ["Id", "Name", "Mother", "Father"]
    }
    ```
    The function will return a list of ancestors for the specified profile:
    ```
    {"status":"ok",,"descendants":[
      {"Id":47228014,"Name":"Slijt-7","Father":47227210,"Mother":47228956},
      {"Id":47228079,"Name":"Slijt-9","Father":47227210,"Mother":47228956},
      {"Id":47228019,"Name":"Slijt-8","Father":47227210,"Mother":47228956}],
    "status":0}
    ```

    In this example, the descendants of the profile "Slijt-6" are "Slijt-7", "Slijt-8" and
    "Slijt-9". If we compare the `UserId` of the father, we can learn that these are his children
    and there are no known grandchildren. This is a simple example; it's much more useful to
    include more fields, such as "FirstName", "LastNameAtBirth", "BirthDate", "DeathDate" and
    "Bio".

    This `get_descendants` function retrieves the descendants of a profile, allowing you to explore
    the family tree and lineage of a person. If you don't know the WikiTree ID of the descendants,
    this function can help you find them.

    This function allows you to understand which descendants are already present in WikiTree, but
    this information may not be complete or accurate, so you must always transfer to the
    LineageAiOrchestrator to perform research to confirm it.
    """,
    tools=[get_descendants],
    output_key="wikitree_descendants"
)
