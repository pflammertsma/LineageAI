import datetime
import requests
import json
import logging
import os
from zoneinfo import ZoneInfo
from google.adk.agents import Agent, BaseAgent, LlmAgent, SequentialAgent

"""
Custom agent for collecting data from OpenArchieven.

This agent orchestrates a sequence of LLM agents to query genealogical records,
combine relevant records and discard irrelevant ones, and combine the result
into a cohesive overview relevant to the query with source links.
"""

AGENT_NAME = "lineage_agent"
APP_NAME = "LineageAI"
GEMINI_MODEL = "gemini-2.0-flash"
PRINT = False

# --- Configure Logging ---
# doesn't work??
# filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '{APP_NAME}.log')
# logging.basicConfig(filename=filename, level=logging.INFO)
# logger = logging.getLogger(__name__)
# logger.info("Invocation start")
if (PRINT): print(f"Invocation start")

def open_archives_search_simple(name: str) -> dict:
    return open_archives_search(name)

def open_archives_search(name: str, archive_code=None, number_show=10, sourcetype=None, 
                        eventplace=None, relationtype=None, country_code=None, 
                        sort=1, lang="en", start=0) -> dict:
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
    tag = "open_archives_search"

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
        if (PRINT): print(f"[{tag}] >>> {base_url} {params}")

        # Make the GET request to the API
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        search_results = response.json()
        if (PRINT): print(f"[{tag}] <<< {search_results}")

        records = []
        for record in search_results["response"]["docs"]:
            records.append(open_archives_show(record["archive_code"], record["identifier"]))

        #logger.info(f"[{tag}] Obtained response: {record}")
        
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
        if (PRINT): print(f"[{tag}] >>> {base_url} {params}")

        # Make the GET request to the API
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the JSON response
        record = response.json()

        # logger.info(f"[{tag}] Obtained response: {record}")
        if (PRINT): print(f"[{tag}] <<< {record}")
        
        # Return the record
        return record
    except requests.RequestException as e:
        # Handle request exceptions
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }

open_archives_agent = Agent(
    name="OpenArchievenResearcher",
    model=GEMINI_MODEL,
    description="""
        Agent to perform initial query to OpenArchieven.
    """,
    instruction="""
        You are a Researcher agent who is responsible for collecting initial data from
        OpenArchieven based on a general query.
        Output the structured data as JSON that is a list of all the records you collected, omitting
        record and archive IDs.
    """,
    tools=[open_archives_search_simple],
    output_key="genealogy_records"
)

reviewer_agent = LlmAgent(
    name="ResultReviewerAgent",
    model=GEMINI_MODEL,
    instruction=""""
        You are a expert Genealogy Reviewer specializing in identifying mistakes in records.
        You review the input records against the combined results and correcting common mistakes.
        You are vigilant of:
        - Incorrectly correlated data from different people of the same name by studying different
          dates of birth, places of birth and parents;
        - Confusions about a role somebody plays in a record, in particular by understanding the
          relevance of parents and spouses in birth, marriage or death records;
        - Unsubstantiated conclusions that are not supported by any records.
        Output a list of conclusions that are ready for the next agent to use for combining the
        records accurately.
    """,
    description="Reviews combined results based on records.",
    output_key="review_comments"
)

combiner_agent = LlmAgent(
    name="RecordCombiner",
    model=GEMINI_MODEL,
    instruction="""
        You are an Record Combiner Assistant specializing in identifying the relationship between
        genealogical results.
        Use the provided genealogical results provided to you, bearing in mind that results may be
        inaccurate and that the previous agent results should be carefully taken into
        consideration.
        Merge the records based on this combination information, noting:
        - Variations in spelling are permitted;
        - Omitted middle names are permitted;
        - Patronymic names (derived from the father's given name) were used prior to 1811, having 
          been replaced by fixed surnames.
        However, if there's a strong signal that there is no relevance, irrelevant irrelevant
        records should be discarded.
        Output a short biography of the person that was queried.
    """,
        # Output the structured data as JSON of the result.
    description="Combines genealogical results from multiple records.",
    output_key="genealogy_result"
 )

root_agent = SequentialAgent(
    name=AGENT_NAME,
    sub_agents=[
        open_archives_agent, reviewer_agent, combiner_agent
    ],
    description=(
        "Agent to answer questions about genealogy in the Netherlands."
    ),
)
