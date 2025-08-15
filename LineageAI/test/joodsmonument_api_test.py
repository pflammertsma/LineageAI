from LineageAI.constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from LineageAI.api.joodsmonument_api import search_joodsmonument
import json

"""
Test the Joods Monument API functions.

To execute:
```
python -m LineageAI.test.joodsmonument_api_test
```
"""
print("Testing searching the Joods Monument...")

test_cases = [
    'Levie van Dam',
]

for query in test_cases:
    print(f'\nsearch_joodsmonument: "{query}"')
    result = search_joodsmonument(query)
    print(json.dumps(result, indent=2))
