from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from .openarchieven import open_archives_search
import json

"""
Test the WikiTree API functions.

To execute:
```
python -m LineageAI.openarchieven_test
```
"""
print("Testing searching OpenArchieven...")

# Example for broad search
result = open_archives_search('{"query": "Wiebre* & Gabe Wiebrens & Hendriks"}')
print("\nopen_archives_search (broad search):")
print(json.dumps(result, indent=2))

# Example for broad search with multiple pages
result = open_archives_search('{"query": "Wiebre", "eventtype": "Overlijden", "number_show": 2}')
print("\nopen_archives_search (multiple pages):")
print(json.dumps(result, indent=2))

# Example for narrow search
result = open_archives_search('{"query": "Wiebre* & Gabe Wiebrens & Hendriks", "eventtype": "Overlijden", "eventplace": "Bolsward"}')
print("\nopen_archives_search:")
print(json.dumps(result, indent=2))
