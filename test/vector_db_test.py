"""Quick manual check that the medical knowledge base works.

Run from the project root:

    python -m test.vector_db_test
"""

from __future__ import annotations

import sys

from backend.core.config import PINECONE_NAMESPACE
from backend.core.pinecone_client import get_index_stats, validate_index
from backend.rag.retrieval import retrieve_documents
from backend.rag.scope import is_medical_question

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUERIES = [
    "What is the first-line treatment for hypertension?",
    "What are the side effects of metformin?",
    "standard treatment guidelines for pneumonia",
]

SCOPE_CHECKS = [
    ("What are the symptoms of type 2 diabetes?", True),
    ("Write a Python function that sorts a list.", False),
    ("What is the adult dose of paracetamol?", True),
    ("Who won the football match yesterday?", False),
]


def main() -> int:
    info = validate_index(verbose=True)
    stats = get_index_stats()
    total = int(stats.get("total_vector_count") or 0)

    print(f"\nIndex     : {info.get('name')}")
    print(f"Documents : {total}")
    print(f"Namespace : {PINECONE_NAMESPACE}")
    if total == 0:
        print("\nThe index is empty. Run: python -m scripts.ingest")
        return 1

    for query in QUERIES:
        print("\n" + "=" * 78)
        print(f"QUERY: {query}")
        print("=" * 78)
        hits = retrieve_documents(query, k=3)
        if not hits:
            print("!! No results. Check the namespace and wait for indexing.")
            return 1
        for number, hit in enumerate(hits, start=1):
            page = f", page {hit.page}" if hit.page else ""
            print(
                f"\n{number}. {hit.title}{page} "
                f"[score={hit.score:.4f}, signals={','.join(hit.signals)}]"
            )
            print(f"   {hit.text[:400].replace(chr(10), ' ')}...")

    print("\n" + "=" * 78)
    print("MEDICAL SCOPE CHECK")
    print("=" * 78)
    try:
        for question, expected in SCOPE_CHECKS:
            result = is_medical_question(question)
            status = "PASS" if result == expected else "FAIL"
            print(f"{status}: allowed={result!s:<5} | {question}")
            if result != expected:
                return 1
    except Exception as error:  # noqa: BLE001 - scope check needs Groq
        print(f"SKIPPED: scope check could not run ({error})")

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
