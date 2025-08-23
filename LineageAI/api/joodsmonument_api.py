from LineageAI.constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from LineageAI.util.utils import rate_limited_get
import requests
import json
import re
from datetime import datetime
import copy
from urllib.parse import quote


PAGE_SIZE = 20
PERMALINK_URL = 'https://www.joodsmonument.nl/rsc/'


def joodsmonument_search(name: str) -> dict:
    """
    Searches the Joods Monument for a given name.

    Args:
        name (str): The name to search for.

    Returns:
        dict: A dictionary containing the search results or an error message.
    """
    tag = "Joodsmonument Search"
    base_url = "https://www.joodsmonument.nl/api/model/search/get"
    
    params = {
        "for": name,
        "pagelen": PAGE_SIZE,
        "with_membership": "true"
    }

    try:
        encoded_name = quote(name)
        url = f"{base_url}?for={encoded_name}&pagelen={PAGE_SIZE}&with_membership=true"
        
        logger.debug(f"[{tag}] >>> {url}")

        response = rate_limited_get(url, timeout=10)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"[{tag}] <<< {data}")

        if data.get("status") == "ok" and "result" in data and "result" in data["result"]:
            doc_ids = data["result"]["result"]
            results = []
            for doc_id in doc_ids:
                doc = joodsmonument_get_document(doc_id, fast=True)
                if doc.get("status") == "ok":
                    results.append(doc["document"])
                else:
                    # Log the error and continue
                    logger.error(f"[{tag}] Failed to retrieve document {doc_id}: {doc.get('error_message')}")
            return {
                "status": "ok",
                "results": results
            }
        elif data.get("status") == "ok":
            return {
                "status": "ok",
                "results": []
            }
        else:
            return {
                "status": "error",
                "error_message": f"API returned status '{data.get('status')}'"
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"[{tag}] API request failed: {e}")
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }
    except json.JSONDecodeError:
        logger.error(f"[{tag}] Failed to decode JSON response")
        return {
            "status": "error",
            "error_message": "Failed to decode JSON response"
        }


def joodsmonument_get_document(doc_id: int, fast=False) -> dict:
    """
    Retrieves a specific document from the Joods Monument.

    Args:
        doc_id (int): The ID of the document to retrieve.

    Returns:
        dict: A dictionary containing the specified fields from the document or an error message.
    """
    tag = "Joodsmonument Get Document"
    url = f"https://www.joodsmonument.nl/api/model/rsc/get/{doc_id}"

    fields_to_extract = [
        "page_url_abs", "id", "title", "name_first", "name_surname_prefix",
        "name_surname", "gender", "date_start", "date_end", "decease_city",
        "birth_city", "birth_country", "address_street_1", "address_city",
        "occupation", "is_a", "depiction_url", "body"
    ]

    try:
        logger.debug(f"[{tag}] >>> {url}")
        response = rate_limited_get(url, timeout=10, fast=fast)
        response.raise_for_status()

        data = response.json()
        logger.debug(f"[{tag}] <<< {data}")

        if data.get("status") == "ok" and "result" in data:
            result = data["result"]
            extracted_data = {field: result.get(field) for field in fields_to_extract}
            
            processed_data = {}
            for key, value in extracted_data.items():
                if value is None:
                    continue

                if isinstance(value, dict) and value.get("_type") == "trans" and "tr" in value:
                    tr = value["tr"]
                    if "nl" in tr:
                        processed_data[key] = tr["nl"]
                    elif tr:
                        processed_data[key] = next(iter(tr.values()))
                else:
                    processed_data[key] = value

            return {
                "status": "ok",
                "document": processed_data
            }
        else:
            return {
                "status": "error",
                "error_message": f"API returned status '{data.get('status')}' or result not found for id {doc_id}"
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"[{tag}] API request failed for id {doc_id}: {e}")
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }
    except json.JSONDecodeError:
        logger.error(f"[{tag}] Failed to decode JSON response for id {doc_id}")
        return {
            "status": "error",
            "error_message": "Failed to decode JSON response"
        }


def joodsmonument_read_document(url_or_id: str) -> bytes | dict:
    """
    Retrieves the raw content from a Joods Monument URL or document ID.

    If the parameter is not a URL, it is assumed to be a document ID.

    Args:
        url_or_id (str): The URL or document ID to retrieve.

    Returns:
        bytes | dict: The raw content of the response or an error message.
    """
    tag = "Joodsmonument Get URL"
    url = str(url_or_id)
    if not url.startswith("http"):
        if not url.isnumeric():
            return {
                "status": "error",
                "error_message": "Invalid input: Must be a URL or a numeric document ID"
            }
        url = f"{PERMALINK_URL}{url}"

    if not url.startswith("https://www.joodsmonument.nl"):
        return {
            "status": "error",
            "error_message": "Invalid URL: Must start with 'https://www.joodsmonument.nl'"
        }

    try:
        logger.debug(f"[{tag}] >>> {url}")
        response = rate_limited_get(url, timeout=10)
        response.raise_for_status()
        return response.content

    except requests.exceptions.RequestException as e:
        logger.error(f"[{tag}] API request failed for url {url}: {e}")
        return {
            "status": "error",
            "error_message": f"API request failed: {str(e)}"
        }
