import os
import logging
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional, Tuple
from .embedding import embed_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dimension: int = 384, index_path: str = "scraped_data"):
        """
        Initialize the vector store using FAISS
        
        Args:
            dimension: Dimension of embeddings
            index_path: Path to save/load the index data
        """
        self.dimension = dimension
        self.index_path = index_path
        # Use IndexIDMap2 for better CPU performance
        self.index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))
        self.texts = []  # List to store document chunks
        self.metadata = []  # List to store metadata
        
        # Try to load existing data
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        embedded_file = os.path.join(self.index_path, 'embedded_content.json')
        index_file = os.path.join(self.index_path, 'faiss_index.bin')
        
        try:
            if os.path.exists(embedded_file) and os.path.exists(index_file):
                # Load embedded content
                with open(embedded_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load chunks and metadata
                chunks = data['chunks']
                embeddings = []
                
                for chunk in chunks:
                    self.texts.append(chunk['content'])
                    self.metadata.append({
                        'url': chunk['url'],
                        'title': chunk['title'],
                        'chunk_index': chunk['chunk_index']
                    })
                    embeddings.append(chunk['embedding'])
                
                # Load FAISS index
                self.index = faiss.read_index(index_file)
                
                # Add embeddings if index is empty
                if self.index.ntotal == 0 and embeddings:
                    embeddings_array = np.array(embeddings).astype('float32')
                    self.index.add(embeddings_array)
                
                logger.info(f"Loaded existing index with {len(self.texts)} documents")
            else:
                logger.info("No existing index found, creating new one")
        
        except Exception as e:
            logger.error(f"Error loading index: {str(e)}")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.texts = []
            self.metadata = []
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """
        Add documents to the vector store
        
        Args:
            documents: List of document dictionaries with content and metadata
            
        Returns:
            bool: True if successful
        """
        try:
            # Batch process embeddings for better performance
            contents = [doc['content'] for doc in documents]
            embeddings = embed_text(contents)  # Modified to handle batch
            
            # Store texts and metadata
            for doc in documents:
                self.texts.append(doc['content'])
                self.metadata.append({
                    'url': doc.get('url', ''),
                    'title': doc.get('title', ''),
                    'chunk_index': doc.get('chunk_index', 0)
                })
            
            # Add to FAISS index with IDs
            embeddings_array = np.array(embeddings).astype('float32')
            ids = np.arange(len(self.texts) - len(documents), len(self.texts))
            self.index.add_with_ids(embeddings_array, ids)
            
            # Save the updated index
            self._save_index()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False
    
    def search(self, query_embedding: List[float], top_k: int = 5, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query_embedding: The query embedding vector
            top_k: Number of results to return
            threshold: Similarity threshold (0-1), higher means more similar
            
        Returns:
            List of documents with their metadata
        """
        try:
            # Convert query embedding to numpy array
            query_array = np.array([query_embedding]).astype('float32')
            
            # Search the index with more candidates
            k = min(top_k * 2, len(self.texts))  # Get more candidates initially
            distances, indices = self.index.search(query_array, k)
            
            # Convert distances to similarity scores (0-1)
            # For IP (inner product) index, higher is better
            similarities = distances[0] / np.max(distances[0])
            
            # Filter and sort results by similarity
            results = []
            seen_urls = set()
            
            for i, (idx, similarity) in enumerate(zip(indices[0], similarities)):
                if idx != -1 and similarity >= threshold:
                    url = self.metadata[idx]['url']
                    
                    # Get surrounding context if from same document
                    content = self.texts[idx]
                    chunk_index = self.metadata[idx]['chunk_index']
                    
                    # Look for adjacent chunks from same URL
                    prev_chunk = ""
                    next_chunk = ""
                    
                    # Check previous chunk
                    prev_idx = idx - 1
                    if prev_idx >= 0 and self.metadata[prev_idx]['url'] == url:
                        prev_chunk = self.texts[prev_idx]
                        
                    # Check next chunk
                    next_idx = idx + 1
                    if next_idx < len(self.texts) and self.metadata[next_idx]['url'] == url:
                        next_chunk = self.texts[next_idx]
                    
                    # Combine chunks with markers
                    if prev_chunk or next_chunk:
                        content = "\n".join(filter(None, [prev_chunk, content, next_chunk]))
                    
                    if url not in seen_urls:  # Only add first/best chunk from each URL
                        results.append({
                            'content': content,
                            'metadata': self.metadata[idx],
                            'score': float(similarity)
                        })
                        seen_urls.add(url)
                    
                    if len(results) >= top_k:
                        break
            
            # Sort by similarity score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error searching index: {str(e)}")
            return []
    
    def _save_index(self):
        """Save the FAISS index and related data"""
        try:
            os.makedirs(self.index_path, exist_ok=True)
            
            # Save FAISS index
            index_file = os.path.join(self.index_path, 'faiss_index.bin')
            faiss.write_index(self.index, index_file)
            
            # Save texts and metadata
            data_file = os.path.join(self.index_path, 'vector_store_data.json')
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'texts': self.texts,
                    'metadata': self.metadata
                }, f, indent=2)
            
            logger.info(f"Saved index with {len(self.texts)} documents")
            
        except Exception as e:
            logger.error(f"Error saving index: {str(e)}")

def main():
    """Initialize and test the vector store"""
    store = VectorStore()
    logger.info(f"Vector store initialized with {store.index.ntotal} vectors")

if __name__ == "__main__":
    main()
