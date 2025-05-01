import time
from typing import Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 86400):
        """
        Initialize the rate limiter
        
        Args:
            max_requests: Maximum allowed requests per time window
            time_window: Time window in seconds (default: 86400 - 24 hours)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        # Store request counts and timestamp of first request in window
        # Format: {ip_address: (count, first_request_timestamp)}
        self.request_counts: Dict[str, Tuple[int, float]] = {}
    
    def is_allowed(self, ip_address: str) -> bool:
        """
        Check if a request from an IP address is allowed
        
        Args:
            ip_address: The IP address of the requester
            
        Returns:
            bool: True if the request is allowed, False otherwise
        """
        current_time = time.time()
        
        # If IP is not in the dictionary, allow the request
        if ip_address not in self.request_counts:
            return True
        
        count, timestamp = self.request_counts[ip_address]
        
        # Check if the time window has passed
        if current_time - timestamp > self.time_window:
            # Reset the counter for this IP
            self.request_counts[ip_address] = (0, current_time)
            return True
        
        # Check if the maximum requests have been reached
        return count < self.max_requests
    
    def increment(self, ip_address: str) -> None:
        """
        Increment the request count for an IP address
        
        Args:
            ip_address: The IP address of the requester
        """
        current_time = time.time()
        
        if ip_address not in self.request_counts:
            # First request from this IP
            self.request_counts[ip_address] = (1, current_time)
        else:
            count, timestamp = self.request_counts[ip_address]
            
            # Check if we need to reset the window
            if current_time - timestamp > self.time_window:
                self.request_counts[ip_address] = (1, current_time)
            else:
                # Increment the counter
                self.request_counts[ip_address] = (count + 1, timestamp)
        
        # Log if approaching limit
        count = self.request_counts[ip_address][0]
        if count >= self.max_requests * 0.8:
            logger.warning(f"IP {ip_address} has used {count}/{self.max_requests} requests")
