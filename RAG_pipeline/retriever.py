from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_pinecone import PineconeVectorStore
from dotenv import load_dotenv

load_dotenv()

embedding = HuggingFaceBgeEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = PineconeVectorStore(
    index_name="medical-rag",
    embedding=embedding
)

# Context Retriever function

def retrieve_context(query, k=5):
    """
    Retrieve documents and combine them into a single context string.
    """
    
    docs = vectorstore.similarity_search(
        query=query,
        # search_type = 'mmr',
        k=k
    )

    context = "\n\n".join([doc.page_content for doc in docs])

    return context