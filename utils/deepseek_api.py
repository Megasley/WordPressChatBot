import os
import logging
import requests
from typing import List, Dict, Tuple, Any
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get configuration from environment
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "")

# Validate configuration
if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY not set in environment")
if not DEEPSEEK_API_URL:
    logger.warning("DEEPSEEK_API_URL not set in environment")

def format_prompt(
    user_query: str, 
    relevant_contexts: List[Dict], 
    conversation_history: List[Dict[str, str]]
) -> Tuple[str, str, str]:
    """
    Format the prompt for DeepSeek API with context and conversation history
    
    Args:
        user_query: The user's query
        relevant_contexts: List of dictionaries containing content and metadata
        conversation_history: Previous conversation messages
        
    Returns:
        Tuple of (system_prompt, history_text, user_query)
    """
    # Sort contexts by relevance score
    sorted_contexts = sorted(relevant_contexts, key=lambda x: x.get('score', 0), reverse=True)
    
    # Format contexts with their sources
    context_chunks = []
    urls_seen = set()
    
    for chunk in sorted_contexts:
        content = chunk.get('content', '').strip()
        metadata = chunk.get('metadata', {})
        url = metadata.get('url', '')
        title = metadata.get('title', '')
        score = chunk.get('score', 0)
        
        if url and content and score >= 0.75:  # Only use high-confidence matches
            if url not in urls_seen:
                urls_seen.add(url)
                context_chunks.append(
                    f"Source: {title}\n"
                    f"URL: {url}\n"
                    f"Content:\n{content}\n"
                )
    
    context_text = "\n---\n".join(context_chunks)
    
    # Format conversation history
    history_text = ""
    if conversation_history:
        for exchange in conversation_history:
            history_text += f"User: {exchange.get('user', '')}\n"
            history_text += f"Assistant: {exchange.get('ai', '')}\n\n"
    
    # Create the system prompt with context
    system_prompt = (
        "You are the official AI assistant for Bitcoiners.Africa — a Pan-African Bitcoin movement focused on education, freedom, and economic empowerment through Bitcoin.\n\n"

        "You speak to Africans from all walks of life — from students to traders, developers to community organizers — and your job is to explain Bitcoin in a clear, practical, and respectful way. Your tone should be confident, helpful, and culturally aware.\n\n"

        "You have access to two sources of knowledge:\n"
        "1. The full content of bitcoiners.africa (embedded below).\n"
        "2. A wider understanding of Bitcoin usage, tools, education, and adoption trends across Africa.\n\n"

        "HOW TO RESPOND:\n"
        "- Answer naturally — never say 'based on the website' or 'from general knowledge.' Speak with authority.\n"
        "- Use bullet points and headings when needed to make your answers easy to read.\n"
        "- If you're quoting content from the site, quietly include the source URL in [square brackets] right after the point.\n"
        "- If the question touches a topic the site doesn’t cover and you don’t have solid info, say: 'There’s no available information on that topic at the moment.'\n"
        "- At the end of each reply, include a 'Related Pages:' section with links from the site that match the topic.\n\n"

        "EXAMPLE RESPONSE:\n"
        "Bitcoin allows people across Africa to save, earn, and spend without relying on unstable currencies or banks.\n\n"
        "Ways Africans Use Bitcoin:\n"
        "- **Earn:** Through global freelance work and Bitcoin-paying jobs [https://bitcoiners.africa/earn-section/]\n"
        "- **Save:** By stacking sats in wallets like Muun, Phoenix, or Bitnob [https://bitcoiners.africa/save-section/]\n"
        "- **Spend:** Pay for airtime, data, and goods via tools like Sats2Data or local circular economies [https://bitcoiners.africa]\n\n"
        "Related Pages:\n"
        "- Earn Bitcoin: https://bitcoiners.africa/earn-section/\n"
        "- Save Bitcoin: https://bitcoiners.africa/save-section/\n"
        "- Spend Bitcoin: https://bitcoiners.africa\n\n"

        "IMPORTANT RULES:\n"
        "1. Never mention the source of your knowledge directly.\n"
        "2. Cite URLs from the website quietly using [square brackets].\n"
        "3. Always be helpful, culturally grounded, and honest.\n"
        "4. Avoid jargon unless explained simply.\n"
        "5. Speak to empower — your goal is to help Africans take control of their money, safely and wisely.\n\n"

        "Below is the full embedded content from bitcoiners.africa:\n\n"
        f"{context_text}"
    )



    
    return system_prompt, history_text, user_query

def generate_response(
    user_query: str, 
    relevant_contexts: List[Dict], 
    conversation_history: List[Dict[str, str]]
) -> Tuple[str, int]:
    """
    Generate a response using DeepSeek API
    
    Args:
        user_query: The user's query
        relevant_contexts: List of dictionaries containing content and metadata
        conversation_history: Previous conversation messages
        
    Returns:
        Tuple of (response_text, tokens_used)
    """
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_URL:
        logger.warning("Missing DeepSeek API configuration, using demo mode")
        
        # Check if we have any relevant contexts to use
        if relevant_contexts:
            context = relevant_contexts[0]
            content = context.get('content', '')
            metadata = context.get('metadata', {})
            url = metadata.get('url', '')
            title = metadata.get('title', '')
            
            # Format demo response with proper structure
            response = (
                f"According to our website:\n{content} [{url}]\n\n"
                f"Learn More:\n- {title}: {url}"
            )
            return response, 0
            
        # Generic responses for demo mode
        query_lower = user_query.lower()
        demo_response = ""
        
        if "hello" in query_lower or "hi" in query_lower:
            demo_response = "Hello! I'm your AI assistant for bitcoiners.africa. How can I help you today?"
        elif "bitcoin" in query_lower or "crypto" in query_lower:
            demo_response = "I can help you learn about Bitcoin and cryptocurrency in Africa. Please ask a specific question about our resources and programs."
        else:
            demo_response = "I'm in demo mode. To get accurate information from our website, please configure the DeepSeek API key. I can then provide specific information from bitcoiners.africa with relevant page links."
        
        return demo_response + "\n\nLearn More:\n- Homepage: https://bitcoiners.africa", 0
    
    try:
        system_prompt, history_text, user_query = format_prompt(
            user_query, relevant_contexts, conversation_history
        )
        
        # Prepare messages for the API
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for exchange in conversation_history:
                messages.append({"role": "user", "content": exchange.get('user', '')})
                messages.append({"role": "assistant", "content": exchange.get('ai', '')})
        
        # Add the current user query
        messages.append({"role": "user", "content": user_query})
        
        # Call DeepSeek API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        payload = {
            "model": "deepseek-chat",  # Use appropriate model name
            "messages": messages,
            "temperature": 0.3,  # Lower temperature for more consistent, factual responses
            "max_tokens": 1000
        }
        
        response = requests.post(
            DEEPSEEK_API_URL,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            response_text = response_data["choices"][0]["message"]["content"]
            tokens_used = response_data["usage"]["total_tokens"]
            return response_text, tokens_used
        else:
            logger.error(f"DeepSeek API error: {response.status_code}, {response.text}")
            return f"I encountered an error while processing your request. (Error: {response.status_code})", 0
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return "I'm sorry, but I encountered an error while processing your request.", 0
