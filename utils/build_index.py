import json
from vectorstore import VectorStore

# Path to your embedded content
embedded_file = "./scraped_data/embedded_content.json"

# Load the embedded content
with open(embedded_file, "r", encoding="utf-8") as f:
    data = json.load(f)

chunks = data["chunks"]

# Initialize the vector store
store = VectorStore()

# Add all chunks to the vector store
store.add_documents(chunks)

print(f"Added {len(chunks)} chunks to the vector store and saved the index.")