import os

from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer

load_dotenv()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def main():
    input_file = "coaching_notes_redacted.txt"
    index_name = "coaching-notes"

    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_text(text, chunk_size=500, overlap=100)
    print(f"Split into {len(chunks)} chunks.")

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Connecting to Pinecone...")
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment.")
    pc = Pinecone(api_key=api_key)

    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print("Index created.")
    else:
        print(f"Index '{index_name}' already exists.")

    index = pc.Index(index_name)

    print(f"\nEmbedding and upserting {len(chunks)} chunks...\n")
    vectors = []
    for i, chunk in enumerate(chunks):
        embedding = model.encode(chunk).tolist()
        vectors.append({
            "id": f"chunk-{i}",
            "values": embedding,
            "metadata": {"text": chunk},
        })
        print(f"  Prepared chunk {i + 1}/{len(chunks)} ({len(chunk.split())} words)")

    index.upsert(vectors=vectors)

    print(f"\nDone.")
    print(f"  Chunks upserted: {len(vectors)}")
    print(f"  Index: {index_name}")


if __name__ == "__main__":
    main()