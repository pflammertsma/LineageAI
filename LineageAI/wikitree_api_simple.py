"""
wikitree_api.py

A simple Python interface for the WikiTree API using requests.
See: https://github.com/wikitree/wikitree-api
"""

from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from .wikitree_api import get_relatives, search_profiles
import json
from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent


AGENT_MODEL = MODEL_FAST
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
    `get_profile` function as described in the section below.

    The WikiTree API responds with structured data containing the following fields:

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

    Take careful note that `Name` is in fact the WikiTree ID, which is alphanumeric and used
    to match profiles. If another profile references a WikiTree ID, it is the same person even if
    the link may reference a different name.

    You must always prefer using the WikiTree ID when referencing profiles. For example, `Slijt-6`
    is the WikiTree ID profile in the URL https://www.wikitree.com/wiki/Slijt-6.

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
    - `get_profile`: Retrieves a well-rounded profile for a person using the WikiTree API,
        including their basic info, full biography and details about their parents, siblings,
        spouses and children.

    GETTING A PROFILE
    -----------------

    Invoke `search_profiles` with a WikiTree ID. For example, if you are simply provided with the
    WikiTree ID "Slijt-6", you must use the `get_profile` function as follows:

    ```
    get_profile("Slijt-6")
    ```

    This enables you to understand what a person's name is from just a WikiTree ID.

    This `get_profile` function is the essential function to retrieve the entire content of a
    WikiTree profile, including the biography.

    After retrieving the profile, you must immediately continue with a next step with the goal of
    performing additional research:
    1. Perform more queries to WikiTree to understand which information is already available, such
        as ancestors and descendants, or obtaining the profiles of known family members.
    2. If the profile is incomplete, you must transfer to the LineageAiOrchestrator to ask it to
        look for archival records, historical documents, or other sources outside of WikiTree.

    You must always transfer to the LineageAiOrchestrator before concluding your interaction with
    the user.

    Example output:

```
get_profile_simple:
{
  "status": "ok",
  "person": {
    "Name": "Hendriks-3273",
    "BirthDate": "1765-01-18",
    "BirthLocation": "Bolsward, Friesland, Nederland",
    "DeathDate": "1771-00-00",
    "DeathLocation": "Friesland, Nederland",
    "FirstName": "Obe",
    "MiddleName": "",
    "LastNameAtBirth": "Hendriks",
    "LastNameCurrent": "Lammertsma",
    "bio": "...",
    "Father": { ... },
    "Mother": { ... },
    "Spouses": [ ... ],
    "Children": [ ... ],
    "Siblings": [ ... ]
  }
}
```

    In th eabove example, the profile is about Obe Hendriks, who was later named Obe (Hendriks)
    Lammertsma, born in 1765 and died around 1771.

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

    UPDATING A BIOGRAPHY
    --------------------

    You are unable to update a biography directly using the WikiTree API. Instead, you must
    transfer to the LineageAiOrchestrator.

    PERFORMING RESEARCH
    -------------------

    You are unable to perform any genealogical research and must always transfer to the
    LineageAiOrchestrator to do so.

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

    WikiTree is NOT a source of truth. Profiles may be inaccurate, incomplete or outright wrong.
    You mustn't assume that the profile data is accurate unless explicitly instructed or you have
    validated data against records from the researcher agent.

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
    tools=[get_profile, search_profiles],
    output_key="wikitree_profile"
)
