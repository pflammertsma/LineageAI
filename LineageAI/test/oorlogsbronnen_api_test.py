import json
from LineageAI.api.oorlogsbronnen_api import oorlogsbronnen_search, oorlogsbronnen_read_person
from LineageAI.util.utils import print_truncated


"""
Test the Oorlogsbronnen API functions.

To execute:
```
python -m LineageAI.test.oorlogsbronnen_api_test
```
"""
print("Testing searching Oorlogsbronnen...")

query = "Emma van Dam"
print(f'\noorlogsbronnen_search: "{query}"')
result = oorlogsbronnen_search(query)
print(json.dumps(result, indent=2))


person_id = "ef6921e2-9f3f-4872-96d1-4d45797df390"
print(f'\noorlogsbronnen_read_person: "{person_id}"')
person_result = oorlogsbronnen_read_person(person_id)
print(json.dumps(person_result, indent=2))
