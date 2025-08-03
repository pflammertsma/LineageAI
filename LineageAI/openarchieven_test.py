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

test_cases = [
    '{"query": "Gabe Wiebrens & Hendriks 1900-1950"}',
    '{"query": "Gabe Wiebrens 1900-1950 Hendriks"}',
    '{"query": "Wiebre", "eventtype": "Overlijden", "eventtype": "Overlijden", "eventplace": "Bolsward"}',
    '{"query": "Wiebre* & Gabe Wiebrens & Hendriks"}',
    '{"query": "Wiebre", "eventtype": "Overlijden", "number_show": 2}',
    '{"query": "Wiebre* & Gabe Wiebrens & Hendriks", "eventtype": "Overlijden", "eventplace": "Bolsward"}',
]

for query in test_cases:
    print(f'\nopen_archives_search: "{query}"')
    result = open_archives_search(query)
    print(json.dumps(result, indent=2))
