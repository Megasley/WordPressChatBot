/**
 * African Bitcoin Sidekick Chat Widget
 */

(function() {
  // Initialize the widget when the DOM is fully loaded
  document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('wp-ai-chatbot-container');
    const chatWindow = document.getElementById('wp-ai-chatbot-window');
    const messages = document.getElementById('wp-ai-chatbot-messages');
    const input = document.getElementById('wp-ai-chatbot-input');
    const sendButton = document.getElementById('wp-ai-chatbot-send');
    const closeButton = document.getElementById('wp-ai-chatbot-close');
    const icon = document.getElementById('wp-ai-chatbot-icon');
    const searchButtons = document.querySelectorAll('.wp-ai-chatbot-search-button');
    
    let isOpen = false;
    let currentSession = null;
    let isLoading = false;
    
    // Initialize session
    function initSession() {
        currentSession = {
            id: generateSessionId(),
            messages: []
        };
    }
    
    // Generate random session ID
    function generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }
    
    // Toggle chat window
    function toggleChat() {
        isOpen = !isOpen;
        chatWindow.classList.toggle('active', isOpen);
        if (isOpen && !currentSession) {
            initSession();
        }
    }

    // Show loading indicator
    function showLoading() {
        isLoading = true;
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'wp-ai-chatbot-message wp-ai-chatbot-loading';
        loadingDiv.innerHTML = '<div class="wp-ai-chatbot-typing-indicator"><span></span><span></span><span></span></div>';
        messages.appendChild(loadingDiv);
        messages.scrollTop = messages.scrollHeight;
        
        // Disable input and send button while loading
        if (input) input.disabled = true;
        if (sendButton) sendButton.disabled = true;
    }

    // Hide loading indicator
    function hideLoading() {
        isLoading = false;
        const loadingDiv = document.querySelector('.wp-ai-chatbot-loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
        
        // Re-enable input and send button
        if (input) input.disabled = false;
        if (sendButton) sendButton.disabled = false;
    }
    
    // Add message to chat
    function addMessage(content, isUser = false, messageIndex = null) {
        // Remove welcome message if it exists
        const welcome = document.getElementById('wp-ai-chatbot-welcome');
        if (welcome) {
            welcome.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `wp-ai-chatbot-message ${isUser ? 'wp-ai-chatbot-user-message' : 'wp-ai-chatbot-ai-message'}`;
        
        // Create message content wrapper
        const contentDiv = document.createElement('div');
        contentDiv.className = 'wp-ai-chatbot-message-content';
        
        // Parse markdown for AI messages only
        if (!isUser) {
            contentDiv.innerHTML = parseMarkdown(content);
        } else {
            contentDiv.textContent = content;
        }
        
        messageDiv.appendChild(contentDiv);
        
        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'wp-ai-chatbot-message-time';
        timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        messageDiv.appendChild(timestamp);
        
        // Add regenerate button for AI messages
        if (!isUser && messageIndex !== null) {
            const regenerateButton = document.createElement('button');
            regenerateButton.className = 'wp-ai-chatbot-regenerate';
            regenerateButton.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16">
                    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
                </svg>
                Regenerate response
            `;
            
            // Add click handler for regenerate button
            regenerateButton.addEventListener('click', async () => {
                if (isLoading) return;
                
                try {
                    // Add loading state
                    regenerateButton.classList.add('loading');
                    regenerateButton.disabled = true;
                    
                    const response = await fetch('/api/regenerate', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            session_id: currentSession?.id,
                            message_index: messageIndex
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        // Update the message content
                        contentDiv.innerHTML = parseMarkdown(data.message);
                        
                        // Update timestamp
                        timestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      } else {
                        throw new Error(data.error || 'Failed to regenerate response');
                    }
                } catch (error) {
                    console.error('Error:', error);
                    addMessage('Sorry, I encountered an error while regenerating the response. Please try again.', false);
                } finally {
                    // Remove loading state
                    regenerateButton.classList.remove('loading');
                    regenerateButton.disabled = false;
                }
            });
            
            messageDiv.appendChild(regenerateButton);
        }
        
        messages.appendChild(messageDiv);
        messages.scrollTop = messages.scrollHeight;
        
        if (currentSession) {
            currentSession.messages.push({
                content: content,
                isUser: isUser,
                timestamp: new Date().toISOString()
            });
        }
    }
    
    // Send message to server
    async function sendMessage(content) {
        try {
            showLoading();
            
            const response = await fetch('/api/ask', {
      method: 'POST',
      headers: {
                    'Content-Type': 'application/json'
      },
      body: JSON.stringify({
                    query: content,
                    session_id: currentSession?.id
          })
        });
            
            const data = await response.json();
            
            hideLoading();
            
            if (response.ok) {
                addMessage(data.response, false, data.message_index);
            } else {
                throw new Error(data.error || 'Failed to get response');
            }
        } catch (error) {
      console.error('Error:', error);
            hideLoading();
            addMessage('Sorry, I encountered an error. Please try again.', false);
        }
    }
    
    // Handle user input
    function handleInput() {
        const content = input.value.trim();
        if (content && !isLoading) {
            addMessage(content, true);
            input.value = '';
            sendMessage(content);
        }
    }
    
    // Handle suggested search
    function handleSuggestedSearch(event) {
        event.preventDefault();
        event.stopPropagation(); // Prevent event from bubbling up
        
        const button = event.currentTarget;
        
        // Prevent duplicate submissions
        if (isLoading || button.classList.contains('clicked')) {
            return;
        }
        
        // Mark button as clicked to prevent duplicate submissions
        button.classList.add('clicked');
        
        const query = button.textContent.trim();
        
        // Send the query
        addMessage(query, true);
        sendMessage(query);
        
        // Update button states
        searchButtons.forEach(btn => {
            btn.classList.remove('active');
            btn.classList.remove('clicked'); // Remove clicked state from all buttons
        });
        button.classList.add('active');
    }
    
    // Event Listeners
    if (icon) {
        icon.addEventListener('click', toggleChat);
    }
    if (closeButton) {
        closeButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleChat();
        });
    }
    if (sendButton) {
        sendButton.addEventListener('click', (e) => {
            e.preventDefault();
            handleInput();
        });
    }
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleInput();
            }
        });
    }
    
    // Remove any existing click listeners from search buttons
    searchButtons.forEach(button => {
        button.replaceWith(button.cloneNode(true));
    });
    
    // Add fresh click listeners to search buttons
    document.querySelectorAll('.wp-ai-chatbot-search-button').forEach(button => {
        button.addEventListener('click', handleSuggestedSearch);
    });
    
    // Close on click outside
    document.addEventListener('click', function(e) {
        if (isOpen && !container.contains(e.target)) {
            toggleChat();
        }
    });

    // Initialize chat widget
    console.log('Chat widget initialized');
  });
})();
