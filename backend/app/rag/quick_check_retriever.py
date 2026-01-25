from app.rag.retriever import similarity_search_with_scores, retrieve_policy_chunks_strict


def main():
    query = "Do you require photos for a warranty claim?"

    print("=== Raw results with scores (lower is better) ===\n")
    results = similarity_search_with_scores(query)
    for i, (d, score) in enumerate(results, start=1):
        print(f"{i}. score={score:.4f} source={d.metadata.get('source')}")
        print(d.page_content[:220].replace("\n", " "))
        print()

    print("\n=== Strict filtered results ===\n")
    docs = retrieve_policy_chunks_strict(query)
    for i, d in enumerate(docs, start=1):
        print(f"--- Result {i} (source: {d.metadata.get('source')}) ---")
        print(d.page_content[:600])
        print()


if __name__ == "__main__":
    main()