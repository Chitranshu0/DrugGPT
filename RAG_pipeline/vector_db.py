from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_pinecone import PineconeVectorStore

from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os

import warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()


# Load PDFs
loader = DirectoryLoader(
    path="/home/swati23cseds006/Gen AI/DrugGPT/RAG_pipeline/Medical Books",
    glob="*.pdf",
    loader_cls=PyMuPDFLoader
)

documents = loader.load()

# Split documents
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)

docs = splitter.split_documents(documents)

# Embedding model
embedding = HuggingFaceBgeEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

index_name = "medical-rag"

# Create index if it doesn't exist
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=384,  # all-MiniLM-L6-v2 output dimension
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

# Store embeddings in Pinecone
vectorstore = PineconeVectorStore.from_documents(
    documents=docs,
    embedding=embedding,
    index_name=index_name
)

# # Query
# query = "What is AIDS?"

# results = vectorstore.similarity_search(
#     query=query,
#     k=5
# )

# # Print results
# for i, doc in enumerate(results, start=1):
#     print(f"\nResult {i}")
#     print("-" * 50)
#     print(doc.page_content[:1000])