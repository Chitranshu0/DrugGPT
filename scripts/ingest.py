"""Index the medical book PDFs into Pinecone.

Run from the project root:

    python -m scripts.ingest
"""

from backend.ingestion.vector_db import ingest_medical_books


def main():
    print("Loading PDFs and uploading chunks to Pinecone...")
    ingest_medical_books()
    print("Done. The vector store is ready.")


if __name__ == "__main__":
    main()
