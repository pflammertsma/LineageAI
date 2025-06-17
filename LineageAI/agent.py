import datetime
import requests
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

def query_open_archives_simple(name: str) -> dict:
    return query_open_archives(name)

def query_open_archives(name: str, archive_code=None, number_show=10, sourcetype=None, 
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
        # Make the GET request to the API
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse and return the JSON response
        return response.json()
    except requests.RequestException as e:
        # Handle request exceptions
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }

root_agent = Agent(
    name="lineage_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent to answer questions about genealogy in the Netherlands."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about genealogy in the Netherlands. You collect data through openarchieven.nl which reflects data from various archives in the Netherlands."
    ),
    tools=[query_open_archives_simple],
)
