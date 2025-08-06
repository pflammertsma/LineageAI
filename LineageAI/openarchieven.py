from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from .utils import rate_limited_get
import requests
import json
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.genai import types
import re
from datetime import datetime
import copy

# After testing, we found that MODEL_FAST is not suitable for this agent due to its limited
# reasoning capabilities, often becoming confused with the data it receives and asking unnecessary
# questions.
AGENT_MODEL = MODEL_MIXED  # Use a mixed model for cost efficiency

PAGE_SIZE = 10

"""
Custom agent for collecting data from OpenArchieven.

This agent orchestrates a sequence of LLM agents to query genealogical records,
combine relevant records and discard irrelevant ones, and combine the result
into a cohesive overview relevant to the query with source links.
"""

def open_archives_get_record(url: str) -> dict:
    #https://www.openarchieven.nl/gra:82abb4f7-6091-c219-f035-2cc346509875
    archive, identifier = parse_openarchieven_url(url)
    return open_archives_show(archive, identifier)


def parse_openarchieven_url(url: str):
    """
    Parses an Open Archieven URL to extract the archive and identifier,
    handling URLs with or without trailing slashes.

    Args:
        url (str): The URL string in the format https://www.openarchieven.nl/{archive}:{identifier}.

    Returns:
        tuple: A tuple containing (archive, identifier) or (None, None) if parsing fails.
    """
    try:
        # Remove any trailing slashes to normalize the URL
        normalized_url = url.rstrip('/')

        # Find the last slash to get the relevant part of the URL
        last_slash_index = normalized_url.rfind('/')
        if last_slash_index == -1:
            return None, None # URL format not as expected (e.g., no slashes after domain)

        # Get the part after the last slash, e.g., "gra:82abb4f7-6091-c219-f035-2cc346509875"
        archive_identifier_part = normalized_url[last_slash_index + 1:]

        # Check if the part is empty after removing a potential trailing slash
        if not archive_identifier_part:
            return None, None

        # Split this part by the colon
        parts = archive_identifier_part.split(':')

        if len(parts) == 2:
            archive = parts[0]
            identifier = parts[1]
            return archive, identifier
        else:
            return None, None # Colon not found or multiple colons, or unexpected format
    except Exception as e:
        print(f"An error occurred during URL parsing: {e}")
        return None, None


def open_archives_search(json_str: str) -> dict:
    """
    Accepts a JSON string, parses it, and invokes open_archives_search with the parsed parameters.
    The JSON should contain keys matching the parameters of open_archives_search.
    """
    try:
        params = json.loads(json_str)
        if not isinstance(params, dict):
            return {"status": "error", "error_message": "JSON must represent an object with search parameters."}
        # Override page/offset handling
        if 'start_offset' in params:
            del params['start_offset']
        params['number_show'] = PAGE_SIZE
        if 'page' in params and isinstance(params['page'], int):
            params['start_offset'] = max(0, params['page'] - 1) * PAGE_SIZE
            del params['page']
        # Make the request and return the results
        result = open_archives_search_params(**params)
        return reformat_results(result)
    except json.JSONDecodeError as e:
        return {"status": "error", "error_message": f"Invalid JSON: {str(e)}"}
    except TypeError as e:
        return {"status": "error", "error_message": f"Parameter error: {str(e)}"}


def reformat_results(result: dict) -> dict:
    """
    Reformats a JSON dictionary from a specific input structure to a cleaner,
    more consolidated output structure.

    Args:
        result: The input dictionary to reformat.

    Returns:
        The reformatted dictionary.
    """
    if 'status' in result and result['status'] == 'error':
        return result
    
    # Modify the result to reflect the current page and total pages
    if 'start_offset' in result and 'results_remaining' in result and 'records' in result:
        current_page = result['start_offset'] // PAGE_SIZE
        total_records = result['start_offset'] + len(result['records']) + result['results_remaining']
        total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE # Ceiling division
        result['page'] = current_page + 1
        result['total_pages'] = total_pages
        del result['start_offset']
        del result['results_remaining']

    if not result or 'records' not in result or not isinstance(result['records'], list):
        return {"status": "error", "error_message": f"Unexpected response format: {result}"}

    # Create a deep copy to avoid modifying the original input dictionary
    reformatted_result = copy.deepcopy(result)

    for record in reformatted_result.get('records', []):
        # --- 1. Consolidate Person and Relation Data ---
        
        relations_map = {}
        # Process Event-Person relations first to establish primary roles
        if 'RelationEP' in record and isinstance(record.get('RelationEP'), list):
            for rel in record['RelationEP']:
                if 'PersonKeyRef' in rel and 'RelationType' in rel:
                    relations_map[rel['PersonKeyRef']] = rel['RelationType']

        # Process Person-Person relations, adding them if a person doesn't already have a role
        if 'RelationPP' in record and isinstance(record.get('RelationPP'), dict):
            relation_pp = record['RelationPP']
            relation_type = relation_pp.get('RelationType')
            person_refs = relation_pp.get('PersonKeyRef', [])
            if relation_type and isinstance(person_refs, list):
                for person_ref in person_refs:
                    if person_ref not in relations_map:
                        relations_map[person_ref] = relation_type
        
        # Build the new, consolidated list of persons, preserving original order
        new_person_list = []
        # Handle case where 'Person' is a single dictionary instead of a list
        if 'Person' in record and isinstance(record['Person'], dict):
            record['Person'] = [record['Person']]

        # Iterate over the (now guaranteed) list of persons
        for person_data in record.get('Person', []):
            pid = person_data.get('@pid')
            
            # Create a new person dict, excluding the '@pid'
            new_person = {k: v for k, v in person_data.items() if k != '@pid'}
            
            # Add the mapped relation type
            if pid and pid in relations_map:
                new_person['RelationType'] = relations_map[pid]
                # Move 'RelationType' to be the first key for consistency with the example
                new_person = {'RelationType': new_person.pop('RelationType'), **new_person}
            
            new_person_list.append(new_person)

        record['Person'] = new_person_list
        
        # Clean up the original relation keys
        record.pop('RelationEP', None)
        record.pop('RelationPP', None)

        # --- 2. Clean Event Data ---
        if 'Event' in record and '@eid' in record.get('Event', {}):
            del record['Event']['@eid']

        # --- 3. Restructure Source Data ---
        if 'Source' in record:
            source = record['Source']

            # Move and rename OpenArchievenLink
            if 'OpenArchievenLink' in record:
                source['OpenArchieven'] = record.pop('OpenArchievenLink')

            # Reformat SourceRemark from a list of objects to a single dictionary
            if 'SourceRemark' in source and isinstance(source.get('SourceRemark'), list):
                source['SourceRemark'] = {
                    item['@Key']: item.get('Value') 
                    for item in source['SourceRemark'] if '@Key' in item
                }

            # Simplify SourceAvailableScans if it's a list of scan objects
            if 'SourceAvailableScans' in source and 'Scan' in source.get('SourceAvailableScans', {}):
                scans_data = source['SourceAvailableScans']['Scan']
                if isinstance(scans_data, list):
                     source['SourceAvailableScans']['Scan'] = [
                         scan['UriViewer'] for scan in scans_data if 'UriViewer' in scan
                     ]
                # Note: If 'Scan' is a single dictionary, it's left unchanged as per the example.

    return reformatted_result


def open_archives_search_params(query: str, archive_code=None, number_show=10, sourcetype=None, 
                        eventplace=None, relationtype=None, eventtype=None, country_code=None, 
                        sort=4, lang="en", start_offset=0) -> dict:
    """Queries the Open Archives API search endpoint.
    
    Args:
        query (str): Search query (required). Can include 2 names separated by & and year/period
        archive_code (str, optional): Filter results on archive code
        number_show (int, optional): Number of results to show (max=100). Defaults to 10
        sourcetype (str, optional): Filter results on source type
        eventplace (str, optional): Filter results on event place
        relationtype (str, optional): Filter results on relation type (e.g., Overledene, Bruid, Kind)
        eventtype (str, optional): Filter results on event type (e.g., Overlijden, Huwelijk, Geboorte, Doop)
        country_code (str, optional): Filter results on country (e.g., nl, be, fr, sr)
        sort (int, optional): Column to sort results (1=Name, 2=Role, 3=Event, 4=Date). Defaults to 1
        lang (str, optional): Language code (nl for Dutch, en for English). Defaults to "en"
        start_offset (int, optional): Initial results to return (for paging). Defaults to 0
        
    Returns:
        dict: JSON response containing the query interpretation and search results.
        
    Raises:
        requests.RequestException: If the API request fails.
    """
    tag = "OpenArchieven Search"

    # Base URL for the Open Archives API search endpoint
    base_url = "https://api.openarchieven.nl/1.1/records/search.json"

    # Sanitize the query:
    # Replace multiple fuzzy search symbols '&~&' with a single '&'
    if query.count("&~&") == 2:
        query = query.replace("&~&", "&", 1)
    # If the query contains both '&~&' and '&', replace all '&~&' with '&'
    if "&~&" in query and "&" in query.replace("&~&", ""):
        query = query.replace("&~&", "&")
    # Replace incomplete year ranges like "1824-" with "1824-<current_year>"
    query = re.sub(r'(\b\d{4})-(?!\d)', rf'\1-{datetime.now().year}', query)
    
    if re.search(r'\d.*[a-zA-Z]', query):
        return {
            "status": "error",
            "error_message": "Query cannot contain names after a date or date range."
        }

    # Validate the query:
    # Check if the query contains more than two ampersands (i.e. more than three names)
    if query.count("&") > 2:
        return {
            "status": "error",
            "error_message": "Query cannot contain more than two '&' symbols; only search using three names at a time or less."
        }
    # Check if a '"' appears anywhere after a '&'
    amp_index = query.find("&")
    if amp_index != -1 and '"' in query[amp_index+1:]:
        return {
            "status": "error",
            "error_message": "Query cannot contain a '\"' character after a '&' symbol."
        }
    
    # Construct parameters dictionary, excluding None values
    params = {
        "name": query,
        "lang": lang,
        "number_show": number_show,
        "start": start_offset,
        "sort": sort
    }
    
    # Add optional parameters if they are provided
    if archive_code:
        params["archive_code"] = archive_code
    if sourcetype:
        params["sourcetype"] = sourcetype
    if eventplace:
        params["eventplace"] = eventplace
    if eventtype:
        params["eventtype"] = eventtype
    if relationtype:
        params["relationtype"] = relationtype
    if country_code:
        params["country_code"] = country_code
    
    try:
        logger.debug(f"[{tag}] >>> {base_url} {params}")

        # Make the GET request to the API
        try:
            response = rate_limited_get(base_url, params=params, timeout=10)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error_message": "API request timed out"
            }

        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        search_results = response.json()
        logger.debug(f"[{tag}] <<< {search_results}")

        logger.info(f"[{tag}] Response body contains {len(search_results)} objects")
        logger.info(f"[{tag}] {search_results["response"]["number_found"]} search results")

        records = []
        if ('docs' in search_results["response"]):
            for doc in search_results["response"]["docs"]:
                record = open_archives_show(doc["archive_code"], doc["identifier"], fast=True)
                record["OpenArchievenLink"] = {
                    "archive_code": doc["archive_code"],
                    "identifier": doc["identifier"]
                }
                records.append(record)
        else:
            # Add a more detailed error message to suggest removing `eventtype` or `eventplace` if it was provided
            error_message = f"No records found. Perhaps your search query was too narrow?"
            parts = []
            if archive_code:
                parts.append("archive_code")
            if sourcetype:
                parts.append("sourcetype")
            if eventplace:
                parts.append("eventplace")
            if eventtype:
                parts.append("eventtype")
            if relationtype:
                parts.append("relationtype")
            if country_code:
                parts.append("country_code")
            if len(parts) > 0:
                error_message = error_message + f" Try removing `{'` or `'.join(parts)}` for a broader search."
            logger.warning(f"[{tag}] {error_message} Response: {search_results["response"]}")
            return {
                "status": "error",
                "error_message": error_message
            }
        
        # Provide the JSON query into the response, but remove irrelevant parts
        return_query = copy.deepcopy(params)
        del return_query["lang"]
        del return_query["number_show"]
        del return_query["start"]
        del return_query["sort"]

        result = {
            "start_offset": start_offset,
            "results_remaining": max(0, search_results["response"]["number_found"]-len(records)-start_offset),
            "query": return_query,
            "records": records
        }

        logger.info(f"[{tag}] Result: {result}")
        
        # Return the record
        return result
    except requests.RequestException as e:
        # Handle request exceptions
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }


def open_archives_show(archive: str, identifier: str, callback="", lang="en", fast=False) -> dict:
    """Queries the Open Archives API /show endpoint.
    
    Args:
        archive (str, required): Code of archive (obtain a list of valid archive codes via Stats/Archives)
        identifier (str, required): Identifier of the record
        callback (str, optional): Function name to be called on JSON data (JSONP).
        lang (str, optional): Language code (nl for Dutch, en for English). Defaults to "en".
        
    Returns:
        dict: JSON response containing the record.
        
    Raises:
        requests.RequestException: If the API request fails.
    """
    tag = "open_archives_show"

    logger.info(f"Reading record {identifier}...")

    # Base URL for the Open Archives API search endpoint
    base_url = "https://api.openarchieven.nl/1.1/records/show.json"
    
    # Construct parameters dictionary, excluding None values
    params = {
        "archive": archive,
        "identifier": identifier,
        "callback": callback,
        "lang": lang
    }
    
    # Add optional parameters if they are provided
    if archive:
        params["archive"] = archive
    if identifier:
        params["identifier"] = identifier
    if callback:
        params["callback"] = callback
    if lang:
        params["lang"] = lang
    
    try:
        logger.debug(f"[{tag}] >>> {base_url} {params}")

        # Make the GET request to the API
        try:
            response = rate_limited_get(base_url, params=params, timeout=10, fast=fast)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error_message": "API request timed out"
            }
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        record = response.json()

        # logger.info(f"[{tag}] Obtained response: {record}")
        logger.debug(f"[{tag}] <<< {record}")
        
        # Return the record
        return record
    except requests.RequestException as e:
        # Handle request exceptions
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }


def open_archives_agent_instructions(context: ReadonlyContext) -> str:
    return """
    You are responsible for reading individual records and performing searches for records from
    OpenArchieven and performing searches.

    The following functions are available to you:
    - `open_archives_get_record`: Read an individual record by its URL. If a user provides a direct
      openarchieven.nl URL, immediately use `open_archives_get_record` to fetch that specific
      record before attempting any other searches.
    - `open_archives_search`: Perform a search for records based on a query.

    Understanding openarchieven.nl URLs:
    
    URLs on openarchieven.nl have the following format:
    https://www.openarchieven.nl/\{archive_code\}:\{identifier\}

    For example, if the archive code is "gra" and the identifier is
    "e551c8d7-361b-edf2-3199-ee3d4978e329", the URL would be:
    https://www.openarchieven.nl/gra:e551c8d7-361b-edf2-3199-ee3d4978e329

    The openarch.nl domain is the same as openarchieven.nl.


    GETTING RECORDS
    ---------------

    To read an individual record, you must invoke `open_archives_get_record` with a URL, e.g.:
    
    open_archives_get_record("https://www.openarchieven.nl/gra:82abb4f7-6091-c219-f035-2cc346509875")

    If you are provided with any openarchieven.nl URLs, you must read the record using
    `open_archives_get_record`. You do NOT need to fetch a record if it was obtained through
    `open_archives_search` because the search results already contain the entire record.

    
    SEARCHING RECORDS
    -----------------
    
    To perform a search, you must extract a search query from the user's input. You must then
    invoke `open_archives_search` with a JSON string that contains the parameters for that
    search query. The JSON should contain keys matching the following parameters:
    - `query`: The query to search for (required). This parameter requires a very specific
        format detaled below.
    - `page`: The page of results to request, for paginated results (for paging, optional;
        default=1).
    - `eventplace`: The event place to filter results on (optional).
    - `eventtype`: The event type to filter results on (optional). One of these values:
        - `Overlijden`: Death
        - `Huwelijk`: Wedding
        - `Geboorte`: Birth
        - `Doop`: Baptism
    - `relationtype`: The relation type to filter results on (optional). One of these values:
        - `Overledene`: Deceased
        - `Bruidegom`: Groom
        - `Bruid`: Bride
        - `Relatie`: Relation (often used to reference a partner in a deceased record)
        - `Kind`: Child
        - `Vader`: Father
        - `Moeder`: Mother
        - `Vader van de bruide`: Father of the bride
        - `Vader van de bruidegom`: Father of the groom
        - `Moeder van de bruid`: Mother of the bride
        - `Moeder van de bruid`: Mother of the bride

    It cannot contain any other parameters; this will result in an error.

    
    QUERY PARAMETER
    ---------------

    Here follows the details of the `query` parameter, starting with a basic search:

    "[name1] [year]"

    Where [name1] is the name of the primary person you are searching for, and [year] is any
    relevant date or date range of a record. Providing [year] is optional.

    To perform a narrower search, you can also combine multiple names into a single search query:

        "[name1] & [name2]"

    Here, [name2] is another person that appears in the same record as the primary individual,
    provided as [name1]. If you do not separate different people's names with an `&` symbol, the
    API will assume you are searching for one person with that name.
    
    To perform an even narrower search, you can include a year, for example:

        "[name1] & [name2] [year]"
        
    The year relates to the date of the record. Searching for marriage records while providing the
    year of birth, for example, will NOT yield the marriage record, because the date of the
    marriage record will of course be much later than their birth.

    To perform an extremely narrow search on three people:

        "[name1] & [name2] & [name3]"

    You cannot search for more than three names at a time.

    You can perform a fuzzy search between precisely two people using `&~&`, but then it must be
    placed precisely between two names:

        "[name1] &~& [name2] [year]"

    Note that `&~&` cannot appear more than once in a query or together with `&`.

    Where:
    - For [name], you can search by exclusion using `-`; e.g. use `Jansen -Aaltje` to include
        "Jansen" and not "Aaltje".
    - For [name], you can search for phonetic matches using `~`: e.g. use `~Rodenburg` to
        find people with names sounding like Rodenburg.
    - For [name], you can search for a specific surname by using `>`: e.g. use `>Rodenburg` to
        find people only with the surname Rodenburg.
    - For [name], you can search for exact matches by using `"`: e.g. use `"Jan Jansen"` to
        find people with the exact name Jan Jansen. However, you can ONLY use this for the first
        person's name; combining multiple names in quotation marks will result incorrectly in no
        matches!
    - For [name], you can search using wildcards by using `?` (for one letter) or `*` (for
        multiple letters): e.g. use `K*sper` to find people with the names Kysper, Kijsper,
        Keijsper, etc.
    - For [year], you can also provide a year range, such as `Jan Jansen 1900-1950`.
    - For [year], you can also provide a specific date, such as `Jan Jansen 29-5-1925` using
        the format [DD-MM-YYYY], although it's not recommended to avoid too narrow searches.

    Some examples:
    - If you are searching for "Jan Jansen born in 1902", you should query the function with
        the argument `Jan Jansen 1902`.
    - If you are is searching for "Jan Jansen born around 1900 and died around 1950", you should
        query the function with the argument `Jan Jansen 1900-1950`.
    - If you are is searching for "Jan Jansen married in 1923", you should simply query the
        function with `Jan Jansen 1923` because there is no way to specify the relevance of the
        record.
    - If you are searching for a marriage between Jan Jansen and Aaltje Zwiers in Zuidwolde on
        May 29, 1923, you should query the function only with the names and year:
        `Jan Jansen &~& Aaltje Zwiers 1923`. This is because the search interface does not
        support searching for places or events, and using specific dates may be overly
        restrictive.
    - To use more than two names in the query, you can can use the alternative syntax (`&`
        instead of `&~&`), but note that it's a very narrow search and it's generally not very
        useful unless other strategies are giving too many results.
    - To uncover a variation of a name, an effective strategy is to search using the names of
        one or both parents, such as `Jan Jansen &~& Hendrik Jansen 1923-1950`. This might seem
        counterintuitive, but it works because both the person you're looking and the other names
        from the query may be included in the record. This can work for birth, marriage, and
        death records.

    You must only provide names and years in the search query, and you must not include additional
    information such as places or events.
    

    RESPONSE
    --------
    
    If your search query contains invalid syntax, the results will simply be empty and you will
    not receive an error.
    
    The absence of a record does not mean that it does not exist, and you must consider the
    possibility that your search has been too narrow.

    You use this search query to search the Open Archives API by calling the `open_archives_search`
    function. The results are ordered chronologically, starting with the oldest records that match.
    Note that the number of results that appear in subsequent pages is stored in
    `total_pages`.

    If there are over 5 pages returned in `total_pages`, the query is too broad and should be
    refined. Otherwise, if `total_pages` is more than 1, you must query the next page using the
    `page` parameter. You do this by incrementing the `page` parameter as you read subsequent
    pages. If the returned value for `page` equals `total_pages`, then you have reached the
    end.

    For example, if you queried the first page with `page: 1`, you would query the second page with
    `page: 2`, etc. Try not to read more than 5 pages to avoid overwhelming the API and to ensure
    that you can process the results effectively.
    

    OTHER PARAMETERS
    ----------------
    
    Before attempting to use other parameters, you must clearly identify the role of the primary
    person in the search, denoted previously with [name1].
    
    To understand how to use `relationtype`, first ask yourself, "Is the person I'm searching for
    the child, parent, spouse, or the event subject?" If you are looking for the birth record of
    [name1], you might consider providing `relationtype` as "Kind", for example.

    Never attempt to include a place name in the search query string; it must be provided as 
    `eventplace` but this should be avoided unless absolutely necessary because it narrows down
    searches due to event locations being recorded on historical municipality names that you may
    not know. You should instead try to narrow down results by location by performing a broad
    search and inspecting the returned location data in the results yourself.

    Generally, you will not need to refine the query using `eventtype`, `relationtype` or
    `eventplace` parameters, as you risk excluding relevant records that may not have the event
    type, relation type or event place you specified. You should only use these parameters if you
    are looking for a specific type of record among a large number of results.

    You should never try to query with a `start_offset` using a query that differs from the for the
    first page as the results will be unpredictable. You must use the knowledge that the record may
    be on subsequent pages to determine when to query next pages using the aforementioned
    functions, because otherwise you might only see results too early to the time frame relevant to
    your search. This is sometimes unavoidable when many results appear while searching with a
    date.

    The best strategy to leaf through many pages of broad results so that you don't miss any
    records that may have misspellings or for instance omit a parent, so long as the total number
    of records to process is not more than 100. The best way to do this is to reduce the names
    provided in the query to just the first or last name of the person you are looking for,
    combined with a range of years that is relevant to the search, then narrowing down from there.
    You must also bear in mind common spelling mistakes and variations.

    
    VALID EXAMPLES
    --------------

    Suppose you are looking for a person named Jan Jansen that you suspect was born around 1900.
    First try to first search for birth records using:
    
      `{"query": "Jan Jansen 1900"}`
    
    If you get too many results, try to add some information about a parent:
    
      `{"query": "Jan Jansen &~& Hendrik Jansen 1900"}`

    If you are still getting very many results, you can also try narrowing down to specific
    records. In this example, we can search for births where Jan Jansen is the father, but beware
    that you will likely miss other good resources like population registers:

      `{"query": "Jan Jansen &~& Aaltje Zwiers", "eventtype": "Geboorte", "relationtype": "Vader"}`

    Conversely, if you are trying to find the birth record of a child without knowing the year, you
    should try to search for the child with the parent's name. For example:
    
      `{"query": "Jan Jansen &~& Hendrik Jansen"}`
    
    If this gives no results, you can try to remove parts of the parents' names, for example:
    
      `{"query": "Jan Jansen &~& Jansen"}`
    
    Another good approach is to search by an educated guess about birth years of the child:

      `{"query": "Jan Jansen 1880-1920"}`
    
    
    INVALID EXAMPLES
    ----------------

    In these examples, we are assuming Jan Jansen and Aaltje Zwiers are married.

    Invalid because it includes a place name inside the query, which is not supported:

      `{"query": "Jan Jansen 1900-1950 Zuidwolde"}`
    
    Invalid because it two people's names are combined without a `&` or `&~&` separating them,
    which will give no results:

      `{"query": "Jan Jansen Aaltje Zwiers"}`

    Invalid because it includes more than two names with `&~&`, which is not supported:

      `{"query": "Jan Jansen &~& Aaltje Zwiers &~& Hendrik Jansen 1925"}`
    
    Invalid because it combines `&~&` with `&`, which is not supported:

      `{"query": "Jan Jansen &~& Aaltje Zwiers & Hendrik Jansen 1925"}`
    
    Invalid because it includes quotation marks around multiple names, which is not supported:

      `{"query": "\\"Jan Jansen\\" &~& \\"Aaltje Zwiers\\" 1925"}`
    
    Invalid because it includes quotation marks around the second person's name, which is not
    supported:

      `{"query": "Jan Jansen &~& \\"Aaltje Zwiers\\" 1925"}`
    
    Invalid because it assumes that Jan Jansen is a child of Aaltje Zwiers (but in our example he
    is her husband):

      `{"query": "Jan Jansen &~& Aaltje Zwiers", "eventtype": "Geboorte", "relationtype": "Kind"}`

    
    REGIONAL CONVENTIONS
    --------------------

    Prior to 1811, it was common to have patronymic surnames. While extremey common, it isn't
    always the case. A daughter of Gabe Lammerts born before 1811 might be born Wiebren Gabes.
    
    There are unlikely to be any birth records in the Netherlands prior to 1811. You will only find
    mention of a birth date in a baptism record, and possibly other records.

    For birth or baptism records before 1811, assume the individual will not have a fixed surname.
    Prioritize searching using only the first name and patronymic and avoid including surnames in
    queries for these early birth/baptism records unless you know the patronymic surnames of the
    parents. Baptism records before 1811 usually do not include a child's surname at all. In the
    previous example of Wiebren Gabes, her baptism record will only list her as Wiebren and you
    should search for it using "Wiebren & Gabe" instead of "Wiebren Gabes de Boer".

    After 1811, family names became mandatory. Entire families will have registered once under the
    head of the family. It's therefore possible that a child born before 1811 may have a different
    family name in a marriage or death record.
    
    Although living status of parents should be included in the marriage records of their children,
    it's possible this information isn't included in the digital record you have access to. If a
    death record for the subject of the biography is not found, but other records (e.g., children's
    marriage records) list the subject as a parent without explicitly stating they are deceased, do
    not conclude that the subject is alive. Instead, state that the death date is unknown and
    include a research note advising to review the original scanned documents of these records to
    confirm the subject's living status, as digital indexes may not always capture all details
    present in the original handwritten records (e.g., 'overleden' or 'wijlen').


    IMPORTANT NOTES
    ---------------

    Provided that records from OpenArchieven are structered in acenstoral relationships, it's
    unlikely that combining names of multiple children will yield results and that you should
    instead search for each child individually, possibly including one of the parents in the search
    query.

    An important aspect to remember is the use of patronymic names before 1811. Baptism records
    were more commonly used before this time, where the child's name only included the first name
    as the last name would be inherited from the father; for example "Jan" as a son of "Hendrik
    Lammerts" would be known as "Jan Hendriks"). A name may change over time; from the previous
    example, if Jan married after 1811 his record migh list him as "Jan Lammertsma" or "Jan
    Hendriks Lammertsma", or whatever the registered family name was.

    An important aspect to remember is the use of patronymic names before 1811. Baptism records
    were more commonly used before this time, where the child's name only included the first name
    as the last name would be inherited from the father; for example "Jan" as a son of "Hendrik
    Lammerts" would be known as "Jan Hendriks"). A name may change over time; from the previous
    example, if Jan married after 1811 his record migh list him as "Jan Lammertsma" or "Jan
    Hendriks Lammertsma", or whatever the registered family name was.

    Guidelines for searching:
    - Do not attempt to run the exact same search and expect different results!
    - Begin with faily broad searches, containing two names with a fuzzy operator and without any
      filters like `eventtype` or `eventplace`. For example, a good starting point is:
      `{"query": "Jan Jansen &~& Aaltje Zwiers"}`
    - You can perform multiple searches, refining your query as needed:
      - If the search resulted in no results, it was too narrow. Broaden it by being less specific:
        - Always first consider removing the `eventplace` filter, as historical place names can
          vary or be less precise.
        - Then try removing the `eventtype` filter to capture records categorized broadly (e.g.,
          'Registratie' or 'Overige'). This enables you to find records like 'Bevolkingsregister'
          (Population Register) or 'Gezinskaart' (Family Card), which often contain event details
          (birth, marriage, death) but are categorized as general registrations;
        - Expand the year or year range significantly, preferring to omit any range at all,
          especially for older records where exact dates might be less reliable or estimated. This
          also lets you capture related records outside the expected date range, such as childrens'
          records after the date or population registers with an earlier date, but compiled over
          longer periods.
        - If direct searches for an individual's birth/baptism are unsuccessful, pivot to searching
          for related individuals (e.g., parents' marriage, siblings' births) using their names and
          estimated dates. These records often contain details about parents that can indirectly
          confirm the primary individual's family.
      - If the search was too broad, resulting in too many results, narrow it by being more
        specific:
        - Narrowing down year ranges;
        - Including first names and/or surnames of ancestors or descendants using the `&` or `&~&`
          operator;
        - Explicitly filtering by `eventtype`.
    - Pay close attention to the logical operators in search queries:
      - `&` for AND, between two or more names
      - `&~&` for fuzzy AND, between precisely two names only
    - Don't assume that all the information you're seaching for will be in specific records in a
      date range. For example:
      - Missing information about a marriage due to a missing marriage record may be mitigated by
        inferences from baptism or birth records of their children, or, importantly, marriage
        records that may be after one or both of the parents' death.
      - Population registers will have a different `eventtype` and may be missing a date
        altogether, so they might only be discovered by searching without those constraints.
    - Try to keep your total search invocations below 10 before returning to the user to summarize
      your progress and ask whether you should continue. See also the orchestrator's instructions
      on the consultation protocol.

    Once you have concluded your research, you must transfer back to the LineageAiOrchestrator.
    

    AFTER RESPONDING
    ----------------

    You are not able to perform any other functionality than described above. You must transfer to
    the LineageAiOrchestrator for any other tasks, such as accessing WikiTree, formatting or
    updating profiles.
    """

open_archives_agent = LlmAgent(
    name="OpenArchievenResearcher",
    model=AGENT_MODEL,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2, # More deterministic output
        #max_output_tokens=2000 # FIXME Setting restrictions on output tokens is causing the agent not to output anything at all
    ),
    description="""
    You are the OpenArchieven Researcher specialized in performing queries to OpenArchieven, an
    expansive, albeit disjoint, database of genealogical records in the Netherlands.
    """,
    instruction=open_archives_agent_instructions,
    tools=[open_archives_search, open_archives_get_record],
    output_key="genealogy_records"
)
