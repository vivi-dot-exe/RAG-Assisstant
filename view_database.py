import os
import chromadb

def inspect_database():
    db_dir = "./chroma_db"
    print("=" * 80)
    print(f"CHROMADB VECTOR DATABASE INSPECTOR ({os.path.abspath(db_dir)})")
    print("=" * 80)
    
    if not os.path.exists(db_dir):
        print("Database directory does not exist yet. Please process and index PDFs first.")
        return
        
    client = chromadb.PersistentClient(path=db_dir)
    collections = client.list_collections()
    print(f"Found {len(collections)} collection(s) in ChromaDB:\n")
    
    for coll in collections:
        print(f"Collection Name: {coll.name}")
        count = coll.count()
        print(f"Total Chunks Stored: {count}")
        
        if count > 0:
            data = coll.get(include=["documents", "metadatas", "embeddings"])
            ids = data.get("ids", [])
            documents = data.get("documents", [])
            metadatas = data.get("metadatas", [])
            embeddings = data.get("embeddings", [])
            
            print("\n" + "-" * 80)
            print("STORED CHUNKS & METADATA DETAILS:")
            print("-" * 80)
            
            for idx in range(count):
                print(f"Chunk Index: {idx + 1}")
                print(f"  ID:          {ids[idx]}")
                meta = metadatas[idx] if idx < len(metadatas) else {}
                print(f"  File Name:   {meta.get('file_name', 'N/A')}")
                print(f"  Page Number: {meta.get('page_number', 'N/A')}")
                print(f"  Chunk ID:    {meta.get('chunk_id', 'N/A')}")
                if idx < len(embeddings) and embeddings[idx] is not None:
                    print(f"  Embedding:   [{len(embeddings[idx])}-dimensional vector]")
                print(f"  Content Snippet:\n    {repr(documents[idx][:140])}...")
                print("-" * 80)
                
if __name__ == "__main__":
    inspect_database()
