import requests
import json
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, LlmAgent
from google.adk.events import Event, EventActions
from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST

# After testing, we found that MODEL_FAST is not suitable for this agent due to its limited
# reasoning capabilities, often becoming confused with the data it receives and asking unnecessary
# questions.
AGENT_MODEL = MODEL_MIXED  # Use a mixed model for cost efficiency

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
        return open_archives_search_params(**params)
    except json.JSONDecodeError as e:
        return {"status": "error", "error_message": f"Invalid JSON: {str(e)}"}
    except TypeError as e:
        return {"status": "error", "error_message": f"Parameter error: {str(e)}"}


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
    if relationtype:
        params["relationtype"] = relationtype
    if eventtype:
        params["eventtype"] = eventtype
    if country_code:
        params["country_code"] = country_code
    
    try:
        logger.debug(f"[{tag}] >>> {base_url} {params}")

        # Make the GET request to the API
        try:
            response = requests.get(base_url, params=params, timeout=10)
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
                record = open_archives_show(doc["archive_code"], doc["identifier"])
                record["OpenArchievenLink"] = {
                    "archive_code": doc["archive_code"],
                    "identifier": doc["identifier"]
                }
                records.append(record)
        else:
            logger.warning(f"[{tag}] No records found in response: {search_results["response"]}")
            return {
                "status": "error",
                "error_message": "No records found in response"
            }

        result = {
            "start_offset": start_offset,
            "results_remaining": max(0, search_results["response"]["number_found"]-len(records)-start_offset),
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


def open_archives_show(archive: str, identifier: str, callback="", lang="en") -> dict:
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
            response = requests.get(base_url, params=params, timeout=10)
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


open_archives_link_agent = Agent(
    name="OpenArchievenLinker",
    model=AGENT_MODEL,
    description="""
        Agent to perform provide record links to OpenArchieven.
    """,
    instruction="""
        Your sole responsibility is to include link the records you've been provided.

        You must include source attribution URLs for each record based on the archive code and
        identifier.

        For constructing the URLs, use the following format:
        https://www.openarchieven.nl/\{archive_code\}:\{identifier\}

        For example, if the archive code is "gra" and the identifier is
        "e551c8d7-361b-edf2-3199-ee3d4978e329", the URL would be:
        https://www.openarchieven.nl/gra:e551c8d7-361b-edf2-3199-ee3d4978e329

        Output the same structured JSON list you were provided, but with relevant URLs.
    """,
    output_key="genealogy_records"
)

open_archives_agent = LlmAgent(
    name="OpenArchievenResearcher",
    model=AGENT_MODEL,
    description="""
        Agent to perform initial query to OpenArchieven.
    """,
    instruction="""
        You are responsible for reading individual records and performing searches for records from
        OpenArchieven and performing searches.

        To read an individual record, you must invoke `open_archives_get_record` with a URL, e.g.:
        open_archives_get_record("https://www.openarchieven.nl/gra:82abb4f7-6091-c219-f035-2cc346509875")

        If you are provided with any openarchieven.nl URLs, you must read the record using
        `open_archives_get_record`. You do NOT need to fetch a record if it was obtained through
        `open_archives_search` because the search results already contain the entire record.
        
        To perform a search, you must extract a search query from the user's input. You must then
        invoke `open_archives_search` with a JSON string that contains the parameters for that
        search query. The JSON should contain keys matching the following parameters:
        - `query`: The query to search for (required). This parameter requires a very specific
          format detaled below.
        - `start_offset`: The initial results to return (for paging, default=0).
        - `number_show`: The number of results to show (for paging, default=10, max=100).
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

        Here follows the details of the `query` parameter, starting with a basic search:

        "[name] [year]"

        Where [name] is the name of the person the user is searching for, and [year] is any
        relevant date or date range of a record. Providing [year] is optional.

        To perform a narrower search, you can also combine multiple names into a single search
        query:

        "[name1] & [name2]"

        To perform an even narrower search, you can include a year, for example:

        "[name1] & [name2] [year]"

        To perform an extremely narrow search on three people:

        "[name1] & [name2] & [name3]"

        You can perform a fuzzy search between two people using `&~&`, but it can only be between
        two and `&~&` cannot be used more than once in a search:

        "[name1] &~& [name2] [year]"

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
        - If you are searching for "Jan Jansen born in 1900", you should query the function with
          the argument `Jan Jansen 1900`.
        - If you are is searching for "Jan Jansen born in 1900 and died in 1950", you should query
          the function with the argument `Jan Jansen 1900-1950`. It's NOT possible to search from
          with in incomplete range, so be sure to always provide a distant end date if trying to
          narrow down results after a specific date.
        - If you are is searching for "Jan Jansen married in 1925", you should simply query the
          function with `Jan Jansen 1925` because there is no way to specify the relevance of the
          record.
        - If you are searching for a marriage between Jan Jansen and Aaltje Zwiers in Zuidwolde on
          May 29, 1925, you should query the function only with the names and year:
          `Jan Jansen &~& Aaltje Zwiers 1925`. This is because the search interface does not
          support searching for places or events, and using specific dates may be overly
          restrictive.
        - To use more than two names in the query, you can can use the alternative syntax (`&`
          instead of `&~&`), but note that it's a very narrow search and it's generally not very
          useful unless other strategies are giving too many results.
        - To uncover a variation of a name, an effective strategy is to search using the names of
          one or both parents, such as `Jan Jansen &~& Hendrik Jansen 1925-1930`. This might seem
          counterintuitive, but it works because both the person you're looking and the other names
          from the query may be included in the record. This can work for birth, marriage, and
          death records.

        You must only provide names and years in the search query, and you must not include
        additional information such as places or events.
        
        Never attempt to include a place name in the search query string; it must be provided as 
        `eventplace` but generally should be avoided because it narrows down searches due to event
        locations being recorded on historical municipality names that you may not know. You should
        instead try to narrow down results by location by performing a broad search and inspecting
        the returned location data in the results yourself.

        If your search query contains invalid syntax, the results will simply be empty and you will
        not receive an error.
        
        Examples of INVALID queries:
        - `Jan Jansen 1900-1950 Zuidwolde` (invalid because it includes a place name)
        - `Jan Jansen &~& Aaltje Zwiers &~& Hendrik Jansen 1925` (invalid because it includes more
          than two names with `&~&`)
        - `"Jan Jansen" &~& "Aaltje Zwiers" 1925` (invalid because it includes quotation marks
          around multiple names, which is not supported)
        - `Jan Jansen &~& "Aaltje Zwiers" 1925` (invalid because it includes quotation marks
          around the second person's name, which is not supported)
        - `Jan Jansen &~& Aaltje Zwiers 1925-` (invalid because it includes an incomplete date
          range, which is not supported)
        
        You use this search query to search the Open Archives API by calling the
        open_archives_search function. The results are ordered chronologically, starting with
        the oldest records that match. Note that the number of results that appear in subsequent
        pages is stored in `results_remaining`.

        If there are very many records returned in `results_remaining`, the query is likely
        too broad and should be refined.

        Generally, you will not need to refine the query using `eventtype` or `relationtype`
        parameters, as you risk excluding relevant records that may not have the
        event type or relation type you specified. You should only use these parameters if you are
        looking for a specific type of record among a large number of results.

        If there are more results on subsequent pages, you can query them by incrementing the
        `start_offset` parameter by the number of results you want to skip by, which is specified
        in the `results_remaining` value in the response for previous pages. The first page assumes
        `start_offset=0`, so you can omit the `start_offset` parameter for the first page.

        For example, if you queried the first page with `start_offset=0` and `number_show=10`, you
        would query the second page with `start_offset=10`, etc. Try to query 10 records at a time
        to avoid overwhelming the API and to ensure that you can process the results effectively.

        You should never try to query with a `start_offset` using a query that differs from the
        for the first page as the results will be unpredictable. You must use the knowledge that
        the record may be on subsequent pages to determine when to query next pages using the
        aforementioned functions, because otherwise you might only see results too early to the
        time frame relevant to your search. This is sometimes unavoidable when many results
        appear while searching with a date.

        A great strategy to leaf through many pages of broad results so that you don't miss any
        records that may have misspellings or for instance omit a parent, so long as the total
        number of records to process is not more than 100. The best way to do this is to reduce the
        names provided in the query to just the first or last name of the person you are looking
        for, combined with a range of years that is relevant to the search, then narrowing down
        from there. You must also bear in mind common spelling mistakes and variations.

        For example, if you are looking for a person named Jan Jansen born in 1900, try to first
        search for birth records with the query `Jan Jansen 1900`. If you get too many results,
        try to add some information about a parent, such as `Jan Jansen &~& Hendrik Jansen 1900`.

        Conversely, if you are trying to find the birth record of a child without knowing the year,
        you should try to search for the child with the parent's name, such as
        `Jan Jansen &~& Hendrik Jansen`. If this gives no results, you can try to remove parts of
        the parents' names, such as `Jan Jansen &~& Jansen`, or even just `Jan Jansen 1880-1920`,
        where those years are an educated guess about birth years of the child.
        
        Provided that records from OpenArchieven are structered in acenstoral relationships, it's
        unlikely that combining names of multiple children will yield results and that you should
        instead search for each child individually, possibly including one of the parents in the
        search query.

        The absence of a record does not mean that it does not exist, and you must consider the
        possibility that your search has been too narrow.

        You must use open_archives_link_agent to create source links to relevant records.
        
        Output the result of this function to combine the raw data you've been provided as is.
    """,
    sub_agents=[open_archives_link_agent],
    tools=[open_archives_search, open_archives_get_record],
    output_key="genealogy_records"
)
