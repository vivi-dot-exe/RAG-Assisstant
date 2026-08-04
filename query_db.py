import argparse
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def main():
    parser = argparse.ArgumentParser(description="Query a persisted ChromaDB store.")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("--db-dir", type=str, default="./chroma_db", help="Directory where Chroma database is persisted")
    parser.add_argument("--model-name", type=str, default="all-MiniLM-L6-v2", help="Hugging Face embedding model name")
    parser.add_argument("--k", type=int, default=3, help="Number of documents to retrieve")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.db_dir):
        print(f"Error: Chroma database directory '{args.db_dir}' does not exist. Run ingest.py first.")
        return

    print(f"Loading embedding model: {args.model_name}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=args.model_name,
        model_kwargs={'device': 'cpu'}
    )
    
    print(f"Loading ChromaDB from: {args.db_dir}...")
    try:
        vector_db = Chroma(
            persist_directory=args.db_dir,
            embedding_function=embeddings
        )
    except Exception as e:
        print(f"Error loading ChromaDB: {e}")
        return
        
    print(f"Searching for: {repr(args.query)} (retrieving top {args.k} matches)...")
    try:
        # Perform similarity search with score (returns list of Tuple[Document, float])
        # Note: Chroma distance is usually L2 squared, so lower distance is better.
        results = vector_db.similarity_search_with_score(args.query, k=args.k)
    except Exception as e:
        print(f"Error executing similarity search: {e}")
        return
        
    if not results:
        print("No matching documents found.")
        return
        
    print("\nSearch Results:")
    print("-" * 80)
    for idx, (doc, score) in enumerate(results, 1):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "Unknown")
        # In PyPDFLoader, pages are 0-indexed. Let's display both 0-indexed and human-friendly 1-indexed.
        page_display = f"Page {page + 1} (index {page})" if isinstance(page, int) else f"Page {page}"
        
        print(f"Match {idx} | Source: {source} | {page_display} | Score (Distance): {score:.4f}")
        print("-" * 80)
        # Indent content for readability
        content_lines = doc.page_content.strip().split("\n")
        indented_content = "\n".join(f"  {line}" for line in content_lines[:15]) # limit lines output to prevent clutter
        print(indented_content)
        if len(content_lines) > 15:
            print("  ...")
        print("-" * 80)

if __name__ == "__main__":
    main()
