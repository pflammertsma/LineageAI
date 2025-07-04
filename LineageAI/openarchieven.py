import requests
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, LlmAgent
from google.adk.events import Event, EventActions
from .constants import logger, GEMINI_MODEL

"""
Custom agent for collecting data from OpenArchieven.

This agent orchestrates a sequence of LLM agents to query genealogical records,
combine relevant records and discard irrelevant ones, and combine the result
into a cohesive overview relevant to the query with source links.
"""

def open_archives_search_page1(name: str) -> dict:
    return open_archives_search(name, number_show=10, start=0)

def open_archives_search_page2(name: str) -> dict:
    return open_archives_search(name, number_show=10, start=10)

def open_archives_search_page3(name: str) -> dict:
    return open_archives_search(name, number_show=10, start=20)

def open_archives_search_page4(name: str) -> dict:
    return open_archives_search(name, number_show=10, start=30)

def open_archives_search_page5(name: str) -> dict:
    return open_archives_search(name, number_show=10, start=40)

def open_archives_search(name: str, archive_code=None, number_show=60, sourcetype=None, 
                        eventplace=None, relationtype=None, country_code=None, 
                        sort=4, lang="en", start=0) -> dict:
    """Queries the Open Archives API search endpoint.
    
    Args:
        name (str): Search query (required). Can include 2 names separated by & and year/period.
        archive_code (str, optional): Filter results on archive code.
        number_show (int, optional): Number of results to show (max=100). Defaults to 10.
        sourcetype (str, optional): Filter results on source type.
        eventplace (str, optional): Filter results on event place.
        relationtype (str, optional): Filter results on relation type.
        country_code (str, optional): Filter results on country (e.g., nl, be, fr, sr).
        sort (int, optional): Column to sort results (1=Name, 2=Role, 3=Event, 4=Date). Defaults to 1.
        lang (str, optional): Language code (nl for Dutch, en for English). Defaults to "en".
        start (int, optional): Initial results to return (for paging). Defaults to 0.
        
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
        "name": name,
        "lang": lang,
        "number_show": number_show,
        "start": start,
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
            for record in search_results["response"]["docs"]:
                records.append(open_archives_show(record["archive_code"], record["identifier"]))
        else:
            logger.warning(f"[{tag}] No records found in response: {search_results["response"]}")
            return {
                "status": "error",
                "error_message": "No records found in response"
            }

        logger.info(f"[{tag}] Obtained response: {record}")
        
        # Return the record
        return records
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
    model=GEMINI_MODEL,
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
    model=GEMINI_MODEL,
    description="""
        Agent to perform initial query to OpenArchieven.
    """,
    instruction="""
        You are responsible for extracting a search query from the user's input into the following
        format:

        "[name] [year]"

        Where [name] is the name of the person the user is searching for, and [year] is any
        relevant date or date range of a record.

        To perform a narrower search, you can also combine multiple names into a single search
        query, for example:

        "[name1] & [name2] [year]"

        Where:
        - For [name], you can search by exclusion using `-`; e.g. use "Doek -Aaltje" to include
          "Doek" and not "Aaltje".
        - For [name], you can search for phonetic matches using `~`: e.g. use "~Rodenburg" to
          find people with names sounding like Rodenburg.
        - For [name], you can search for a specific surname by using `>`: e.g. use ">Rodenburg" to
          find people only with the surname Rodenburg.
        - For [name], you can search for exact matches by using `"`: e.g. use `"Jan Jansen"` to
          find people with the exact name Jan Jansen.
        - For [name], you can search using wildcards by using `?` (for one letter) or `*` (for
          multiple letters): e.g. use "K*sper" to find people with the names Kysper, Kijsper,
          Keijsper, etc.
        - For [year], you can also provide a year range, such as "Jan Jansen 1900-1950".
        - For [year], you can also provide a specific date, such as "Jan Jansen 12-25-1925" using
          the format [MM-DD-YYYY], although it's not recommended to avoid too narrow searches.

        Some examples:
        - If you are searching for "Jan Jansen born in 1900", you should query the function with
          the argument "Jan Jansen 1900".
        - If you are is searching for "Jan Jansen born in 1900 and died in 1950", you should query
          the function with the argument "Jan Jansen 1900-1950".
        - If you are is searching for "Jan Jansen married in 1925", you should simply query the
          function with "Jan Jansen 1925" because there is no way to specify the relevance of the
          record.
        - If you are searching for a marriage between Jan Jansen and Hillechien Freerks in
          Hoogezand on December 22, 1925, you should query the function only with the names and
          year: "Jan Jansen & Hillechien Freerks 1925". This is because the search interface does
          not support searching for places or events, and using specific dates may be overly
          restrictive.
        - You can have more than two names in the query, but note that it's unlikely to get more
          than precisely one result, so you should only use this if you are looking for a
          specific record that you know exists, although this is not recommended.

        You can only provide names and years in the search query, and you should not include
        additional information such as places or events. No not attempt to include a location in
        the search query and only use the results to cross-reference the information you're looking
        for.
        
        You use this search query to query the Open Archives API by calling the
        open_archives_search_page1 function. If you are looking for a specific record, noting that
        the results are ordered chronologically, you can continue searching the next page by
        calling open_archives_search_page2, open_archives_search_page3, open_archives_search_page4
        and finally open_archives_search_page5. There's no need to search subsequent pages if the
        record you're looking for is not found in the chronological range you've searched so far.
        If the result is not found in the first 50 results, the query is too broad and should be
        refined first.

        You know that records from OpenArchieven are structered in acenstoral relationships, so
        it's unlikely that combining names of multiple children will yield results and that you
        should instead search for each child individually, possibly including one of the parents
        in the search query.

        You must use open_archives_link_agent to create source links to relevant records.
        
        Output the result of this function to combine the raw data you've been provided as is.
    """,
    sub_agents=[open_archives_link_agent],
    tools=[open_archives_search_page1, open_archives_search_page2,
           open_archives_search_page3, open_archives_search_page4,
           open_archives_search_page5],
    output_key="genealogy_records"
)

# open_archives_agent_old = Agent(
#     name=AGENT_NAME,
#     model=GEMINI_MODEL,
#     description="""
#         Agent to perform initial query to OpenArchieven.
#     """,
#     instruction="""
#         You are simply responsible for combining the raw data you've been provided.

#         Output it as is.
#     """,
#     sub_agents=[open_archives_link_agent],
#     tools=[open_archives_search_simple],
#     output_key="genealogy_records"
# )
