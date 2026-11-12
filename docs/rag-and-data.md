# RAG and source-data workflow

Only add PDFs that you are licensed or otherwise authorized to process. Keep them in `data/raw`; this directory is deliberately ignored by Git.

Rebuilding loads every PDF, preserves loader metadata such as the zero-based PDF page, chunks text at 1,000 characters with 150-character overlap, and writes the index to `data/chroma`. At response time DrugGPT converts the page number to a human-facing one-based value, preserving the source path, title, excerpt, and relevance score.

The index can be deleted and rebuilt at any time. It is not a source of truth: retain the original PDFs and verify citations against them. Adjust `DRUGGPT_RELEVANCE_THRESHOLD` only with evaluation data; lower values can make responses less well grounded.
