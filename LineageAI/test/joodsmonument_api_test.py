from LineageAI.constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from LineageAI.api.joodsmonument_api import joodsmonument_read_document
from LineageAI.util.utils import print_truncated

"""
Test the Joods Monument API functions.

To execute:
```
python -m LineageAI.test.joodsmonument_api_test
```
"""

doc_id = '132258'
print(f'\njoodsmonument_read_document: "{doc_id}"')
result = joodsmonument_read_document(doc_id)
print_truncated(result, length=400)