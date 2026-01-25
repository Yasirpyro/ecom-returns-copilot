import os
from dotenv import load_dotenv

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma


def main():
    load_dotenv()

    chroma_dir = os.getenv("CHROMA_DIR", "app/storage/chroma")
    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_base_url)

    db = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings,
        collection_name="ecom_policies",
    )

    query = "Do you require photos for a warranty claim?"
    docs = db.similarity_search(query, k=3)

    print(f"Query: {query}\n")
    for i, d in enumerate(docs, start=1):
        src = d.metadata.get("source", "unknown")
        print(f"--- Result {i} (source: {src}) ---")
        print(d.page_content[:600])
        print()

if __name__ == "__main__":
    main()