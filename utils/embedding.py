import os
import logging
from typing import List, Any
import json
from sentence_transformers import SentenceTransformer
import numpy as np
import torch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding generator
        
        Args:
            model_name: Name of the SentenceTransformer model to use as fallback
        """
        self.model = None
        try:
            self.model = SentenceTransformer(model_name)
            # Enable GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                logger.info("Using GPU for embeddings")
            else:
                logger.info("Using CPU for embeddings")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
    
    def generate_embedding(self, text: str | List[str]) -> List[float] | List[List[float]]:
        """
        Generate embeddings for text(s) using SentenceTransformer
        
        Args:
            text: Single text string or list of texts to embed
            
        Returns:
            List[float] or List[List[float]]: The embedding vector(s)
        """
        try:
            if self.model is None:
                raise ValueError("No embedding model available")
            
            # Handle both single text and batch processing
            is_batch = isinstance(text, list)
            if not is_batch:
                text = [text]
            
            # Generate embeddings
            with torch.no_grad():  # Disable gradient calculation for inference
                embeddings = self.model.encode(text, convert_to_tensor=True)
                if torch.cuda.is_available():
                    embeddings = embeddings.cpu()  # Move to CPU if using GPU
                embeddings = embeddings.numpy()
            
            # Convert to list of floats
            if is_batch:
                return embeddings.tolist()
            return embeddings[0].tolist()
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            if is_batch:
                return [[0.0] * 384 for _ in text]
            return [0.0] * 384

    def process_scraped_content(self, input_file: str, output_file: str, batch_size: int = 32) -> None:
        """
        Process scraped content and generate embeddings
        
        Args:
            input_file: Path to the scraped content JSON file
            output_file: Path to save the embeddings
            batch_size: Number of chunks to process at once
        """
        try:
            # Load scraped content
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chunks = data['chunks']
            total_chunks = len(chunks)
            logger.info(f"Processing {total_chunks} chunks...")
            
            # Process in batches
            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i + batch_size]
                contents = [chunk['content'] for chunk in batch]
                
                # Generate embeddings for the batch
                embeddings = self.generate_embedding(contents)
                
                # Update chunks with embeddings
                for j, embedding in enumerate(embeddings):
                    chunks[i + j]['embedding'] = embedding
                
                if (i + batch_size) % 100 == 0:
                    logger.info(f"Processed {min(i + batch_size, total_chunks)}/{total_chunks} chunks")
            
            # Save results
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            
            logger.info(f"Embeddings generated and saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")

def embed_query(query: str) -> List[float]:
    """
    Generate embeddings for a user query
    
    Args:
        query: The user's query text
        
    Returns:
        List[float]: The embedding vector
    """
    generator = EmbeddingGenerator()
    return generator.generate_embedding(query)

def embed_text(text: str) -> List[float]:
    """
    Generate embeddings for a text chunk
    
    Args:
        text: The text to embed
        
    Returns:
        List[float]: The embedding vector
    """
    generator = EmbeddingGenerator()
    return generator.generate_embedding(text)

def main():
    """Process scraped content and generate embeddings"""
    generator = EmbeddingGenerator()
    
    input_file = os.path.join('scraped_data', 'scraped_content.json')
    output_file = os.path.join('scraped_data', 'embedded_content.json')
    
    generator.process_scraped_content(input_file, output_file)

if __name__ == "__main__":
    main()
