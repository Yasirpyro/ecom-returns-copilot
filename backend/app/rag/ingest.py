import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


def main() -> None:
    # 1) Load environment variables from backend/.env
    load_dotenv()

    policies_dir = Path(os.getenv("POLICIES_DIR", "app/policies"))
    chroma_dir = Path(os.getenv("CHROMA_DIR", "app/storage/chroma"))

    embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    if not policies_dir.exists():
        raise FileNotFoundError(f"POLICIES_DIR not found: {policies_dir.resolve()}")

    # 2) Load all markdown files from policies folder
    loader = DirectoryLoader(
        str(policies_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()
    if not docs:
        raise RuntimeError(f"No policy docs found in: {policies_dir.resolve()}")

    # 3) Split docs into smaller chunks (improves retrieval precision)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=650,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)

    # 4) Embeddings (Ollama)
    embeddings = OllamaEmbeddings(model=embed_model, base_url=ollama_base_url)

    # 5) Rebuild DB cleanly (recommended while developing)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # 6) Build Chroma DB. With langchain-chroma, persistence is automatic
    #    as long as you pass persist_directory.
    _db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(chroma_dir),
        collection_name="ecom_policies",
    )

    print("✅ Vector DB built successfully!")
    print(f"- Policies loaded: {len(docs)}")
    print(f"- Chunks created: {len(chunks)}")
    print(f"- Saved to: {chroma_dir.resolve()}")
    print(f"- Embeddings model: {embed_model}")
    print(f"- Ollama base URL: {ollama_base_url}")


if __name__ == "__main__":
    main()