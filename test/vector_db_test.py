"""Quick manual check that Pinecone retrieval works.

Run from the project root:

    python -m test.vector_db_test
"""

from pprint import pprint

from backend.rag.retrieval import retrieve_context

query = "what is AIDS"

response = retrieve_context(query=query)

pprint(response)
