import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, base_url: str, output_dir: str = "scraped_data", max_depth: int = 3):
        """
        Initialize the web scraper
        
        Args:
            base_url: The main website URL to scrape
            output_dir: Directory to save scraped content
            max_depth: Maximum depth of pages to crawl from the base URL
        """
        self.base_url = base_url.rstrip('/')
        self.output_dir = output_dir
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.content_chunks: List[Dict] = []
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments, query params, and trailing slashes"""
        parsed = urlparse(url)
        # Remove query parameters and fragments
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        # Remove trailing slash if present
        return clean_url.rstrip('/')
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to our target domain and is not just a fragment"""
        try:
            parsed_base = urlparse(self.base_url)
            parsed_url = urlparse(url)
            
            # Normalize URLs for comparison
            base_url_clean = self.normalize_url(self.base_url)
            url_clean = self.normalize_url(url)
            
            # Skip if it's the same page
            if url_clean == base_url_clean:
                return False
            
            # Check if it belongs to our domain and is not a special URL
            return (parsed_url.netloc == parsed_base.netloc and 
                   not url.endswith(('#', '#content')) and
                   not any(x in url for x in ['wp-json', 'wp-admin', 'wp-content', 'feed']))
        except Exception as e:
            logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    def get_url_depth(self, url: str) -> int:
        """Calculate the depth of a URL relative to the base URL"""
        base_path = urlparse(self.base_url).path.strip('/').count('/')
        url_path = urlparse(url).path.strip('/').count('/')
        return url_path - base_path

    def clean_text(self, text: str) -> str:
        """Clean extracted text content"""
        # Remove extra whitespace
        text = " ".join(text.split())
        return text
    
    def extract_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meaningful content from the page with structure"""
        # Remove unwanted elements
        for element in soup.select('nav, footer, header, script, style, iframe, form'):
            element.decompose()
        
        # Get main content
        main_content = soup.select_one('main, article, .content, #content')
        if not main_content:
            main_content = soup
        
        # Initialize structured content
        structured_content = {
            'title': '',
            'headings': [],
            'sections': [],
            'lists': [],
            'full_text': ''
        }
        
        # Extract title
        if soup.title:
            structured_content['title'] = soup.title.string.strip()
        
        # Extract main heading
        main_heading = main_content.find(['h1'])
        if main_heading:
            structured_content['headings'].append({
                'level': 1,
                'text': main_heading.get_text(strip=True)
            })
        
        # Process content by sections
        current_section = {'heading': '', 'content': []}
        current_list = []
        
        for element in main_content.find_all(['h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li']):
            if element.name.startswith('h'):
                # Save previous section if it has content
                if current_section['content']:
                    structured_content['sections'].append(current_section.copy())
                
                # Start new section
                current_section = {
                    'heading': element.get_text(strip=True),
                    'content': []
                }
                structured_content['headings'].append({
                    'level': int(element.name[1]),
                    'text': element.get_text(strip=True)
                })
            
            elif element.name == 'p':
                text = element.get_text(strip=True)
                if text:  # Only add non-empty paragraphs
                    current_section['content'].append(text)
            
            elif element.name in ['ul', 'ol']:
                if current_list:  # Save previous list if exists
                    structured_content['lists'].append(current_list.copy())
                current_list = []
            
            elif element.name == 'li':
                text = element.get_text(strip=True)
                if text:
                    current_list.append(text)
        
        # Add final section and list if they have content
        if current_section['content']:
            structured_content['sections'].append(current_section)
        if current_list:
            structured_content['lists'].append(current_list)
        
        # Combine all text for full-text search
        all_text = []
        for section in structured_content['sections']:
            if section['heading']:
                all_text.append(f"\n## {section['heading']}")
            all_text.extend(section['content'])
        
        structured_content['full_text'] = '\n\n'.join(all_text)
        
        return structured_content
    
    def split_into_chunks(self, structured_content: Dict[str, str], max_tokens: int = 500) -> List[Dict]:
        """Split structured content into semantic chunks"""
        chunks = []
        
        # Helper function to estimate token count
        def estimate_tokens(text):
            return len(text.split())
        
        # Process each section
        for section in structured_content['sections']:
            current_chunk = {
                'heading': section['heading'],
                'content': [],
                'token_count': 0
            }
            
            for paragraph in section['content']:
                para_tokens = estimate_tokens(paragraph)
                
                # If adding this paragraph would exceed max_tokens, save current chunk and start new one
                if current_chunk['token_count'] + para_tokens > max_tokens and current_chunk['content']:
                    chunks.append({
                        'type': 'section',
                        'heading': current_chunk['heading'],
                        'content': '\n\n'.join(current_chunk['content'])
                    })
                    current_chunk = {
                        'heading': section['heading'],
                        'content': [],
                        'token_count': 0
                    }
                
                current_chunk['content'].append(paragraph)
                current_chunk['token_count'] += para_tokens
            
            # Add remaining content in the current chunk
            if current_chunk['content']:
                chunks.append({
                    'type': 'section',
                    'heading': current_chunk['heading'],
                    'content': '\n\n'.join(current_chunk['content'])
                })
        
        # Process lists separately to maintain their structure
        for list_items in structured_content['lists']:
            if list_items:
                chunks.append({
                    'type': 'list',
                    'content': '\n• ' + '\n• '.join(list_items)
                })
        
        return chunks
    
    def scrape_page(self, url: str, current_depth: int = 0) -> None:
        """Scrape content from a single page"""
        # Check depth limit
        if current_depth > self.max_depth:
            logger.debug(f"Skipping {url} - exceeded max depth of {self.max_depth}")
            return
            
        # Normalize URL for visited check
        clean_url = self.normalize_url(url)
        if clean_url in self.visited_urls:
            return
        
        try:
            logger.info(f"Scraping: {clean_url} (depth: {current_depth})")
            response = requests.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract structured content
            structured_content = self.extract_content(soup)
            
            # Split into chunks
            content_chunks = self.split_into_chunks(structured_content)
            
            # Store chunks with metadata
            for chunk in content_chunks:
                if chunk['content'].strip():  # Only store non-empty chunks
                    self.content_chunks.append({
                        'content': chunk['content'],
                        'type': chunk.get('type', 'section'),
                        'heading': chunk.get('heading', ''),
                        'url': clean_url,
                        'title': structured_content['title'],
                        'chunk_index': len(self.content_chunks),
                        'depth': current_depth
                    })
            
            # Mark as visited before processing links to prevent loops
            self.visited_urls.add(clean_url)
            
            # Find and queue new links
            for link in soup.find_all('a', href=True):
                next_url = urljoin(url, link['href'])
                if self.is_valid_url(next_url):
                    next_url_clean = self.normalize_url(next_url)
                    if next_url_clean not in self.visited_urls:
                        self.scrape_page(next_url, current_depth + 1)
            
            time.sleep(1)  # Be nice to the server
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
    
    def scrape_site(self) -> None:
        """Scrape the entire website"""
        try:
            self.scrape_page(self.base_url)
            
            # Save results
            output_file = os.path.join(self.output_dir, 'scraped_content.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'chunks': self.content_chunks,
                    'metadata': {
                        'total_chunks': len(self.content_chunks),
                        'total_pages': len(self.visited_urls),
                        'base_url': self.base_url
                    }
                }, f, indent=2)
            
            logger.info(f"Scraping completed. Processed {len(self.visited_urls)} pages and generated {len(self.content_chunks)} chunks.")
            
        except Exception as e:
            logger.error(f"Error during site scraping: {str(e)}")

def main():
    """Main function to run the scraper"""
    scraper = WebScraper('https://bitcoiners.africa')
    scraper.scrape_site()

if __name__ == "__main__":
    main() 