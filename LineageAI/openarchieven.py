import requests
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, LlmAgent
from google.adk.events import Event, EventActions
from .constants import logger, GEMINI_MODEL

AGENT_NAME = "OpenArchievenResearcher"

"""
Custom agent for collecting data from OpenArchieven.

This agent orchestrates a sequence of LLM agents to query genealogical records,
combine relevant records and discard irrelevant ones, and combine the result
into a cohesive overview relevant to the query with source links.
"""

def open_archives_search_simple(name: str) -> dict:
    return open_archives_search(name)

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
        response = requests.get(base_url, params=params)
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
        response = requests.get(base_url, params=params)
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
    name=AGENT_NAME,
    model=GEMINI_MODEL,
    description="""
        Agent to perform initial query to OpenArchieven.
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
    tools=[open_archives_search_simple],
    output_key="genealogy_records"
)

open_archives_agent = LlmAgent(
    name=AGENT_NAME,
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

        Some examples:
        - If the user is searching for "Jan Jansen born in 1900", you should query
          open_archives_search_simple with the argument "Jan Jansen 1900".
        - If the user is searching for "Jan Jansen born in 1900 and died in 1950", you should
          query open_archives_search_simple with the argument "Jan Jansen 1900-1950".
        - If the user is searching for "Jan Jansen married in 1925", because there is no way to
          specify the relevance of the record, you should query open_archives_search_simple with
          "Jan Jansen 1925".

        You use this search query to query the Open Archives API by calling the
        open_archives_search_simple function.

        You must use open_archives_link_agent to create source links to relevant records.
        
        Output the result of this function to combine the raw data you've been provided as is.
    """,
    sub_agents=[open_archives_link_agent],
    tools=[open_archives_search_simple],
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
