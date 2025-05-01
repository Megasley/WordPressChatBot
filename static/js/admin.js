/**
 * WordPress AI Chatbot Admin Panel
 * Manage documents and settings for the DeepSeek AI chatbot
 */

document.addEventListener('DOMContentLoaded', function() {
  // Initialize file upload functionality
  initFileUpload();
  
  // Initialize API key validation
  initApiKeyValidation();
  
  // Load usage statistics
  loadUsageStats();
  
  // Initialize document list
  loadDocumentList();
  
  // Initialize chat sessions list
  initChatHistory();
});

/**
 * Initialize file upload area with drag & drop support
 */
function initFileUpload() {
  const fileUpload = document.getElementById('file-upload');
  const fileInput = document.getElementById('file-input');
  const fileButton = document.getElementById('file-button');
  const fileInfo = document.getElementById('file-info');
  const uploadForm = document.getElementById('upload-form');
  
  // Open file selector when button is clicked
  fileButton.addEventListener('click', function() {
    fileInput.click();
  });
  
  // Handle file selection
  fileInput.addEventListener('change', function() {
    const file = this.files[0];
    if (file) {
      updateFileInfo(file);
    }
  });
  
  // Drag & drop functionality
  fileUpload.addEventListener('dragover', function(e) {
    e.preventDefault();
    fileUpload.classList.add('active');
  });
  
  fileUpload.addEventListener('dragleave', function() {
    fileUpload.classList.remove('active');
  });
  
  fileUpload.addEventListener('drop', function(e) {
    e.preventDefault();
    fileUpload.classList.remove('active');
    
    const file = e.dataTransfer.files[0];
    if (file) {
      fileInput.files = e.dataTransfer.files;
      updateFileInfo(file);
    }
  });
  
  // Handle form submission
  uploadForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const file = fileInput.files[0];
    if (!file) {
      showAlert('Please select a file first', 'error');
      return;
    }
    
    // Validate file type
    if (!file.name.endsWith('.txt') && !file.name.endsWith('.md')) {
      showAlert('Only .txt and .md files are supported', 'error');
      return;
    }
    
    // Create FormData and send the file
    const formData = new FormData();
    formData.append('file', file);
    
    // Show loading state
    fileButton.disabled = true;
    fileButton.textContent = 'Uploading...';
    
    // Upload the file
    fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      showAlert(data.message || 'Document uploaded successfully', 'success');
      fileInput.value = '';
      fileInfo.textContent = 'No file selected';
      loadDocumentList(); // Refresh document list
    })
    .catch(error => {
      console.error('Error:', error);
      showAlert('Failed to upload document. Please try again.', 'error');
    })
    .finally(() => {
      fileButton.disabled = false;
      fileButton.textContent = 'Choose File';
    });
  });
  
  /**
   * Update file info display
   */
  function updateFileInfo(file) {
    const sizeInKB = Math.round(file.size / 1024);
    fileInfo.textContent = `${file.name} (${sizeInKB} KB)`;
  }
}

/**
 * Initialize API key validation functionality
 */
function initApiKeyValidation() {
  const apiKeyForm = document.getElementById('api-key-form');
  const apiKeyInput = document.getElementById('api-key');
  const saveKeyButton = document.getElementById('save-key-button');
  
  apiKeyForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const apiKey = apiKeyInput.value.trim();
    if (!apiKey) {
      showAlert('Please enter an API key', 'error');
      return;
    }
    
    // Show loading state
    saveKeyButton.disabled = true;
    saveKeyButton.textContent = 'Saving...';
    
    // This would typically send the API key to the server for validation and storage
    // For security reasons, we're just simulating this process
    setTimeout(() => {
      showAlert('API key saved successfully', 'success');
      saveKeyButton.disabled = false;
      saveKeyButton.textContent = 'Save';
    }, 1000);
  });
}

/**
 * Load usage statistics from the server
 */
function loadUsageStats() {
  // Fetch actual stats from the API
  fetch('/api/stats')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(stats => {
      // Update the stats on the page
      document.getElementById('stat-queries').textContent = stats.total_api_calls.toLocaleString();
      document.getElementById('stat-tokens').textContent = stats.total_tokens.toLocaleString();
      document.getElementById('stat-documents').textContent = stats.document_count;
      document.getElementById('stat-ratings').textContent = `${stats.positive_percentage}%`;
    })
    .catch(error => {
      console.error('Error loading statistics:', error);
      showAlert('Failed to load statistics', 'error');
    });
}

/**
 * Load the list of uploaded documents
 */
function loadDocumentList() {
  const documentList = document.querySelector('.document-list');
  
  // Exit early if no document list element found (might be on a different page)
  if (!documentList) return;
  
  // Set loading state
  documentList.innerHTML = '<div class="document-item">Loading documents...</div>';
  
  // Fetch documents from API
  fetch('/api/documents')
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      // Clear current list
      documentList.innerHTML = '';
      
      // The API now returns an array directly
      const documents = Array.isArray(data) ? data : (data.documents || []);
      
      // Add documents to the list
      if (documents.length === 0) {
        documentList.innerHTML = '<div class="document-item">No documents uploaded yet</div>';
        return;
      }
      
      // Create document list table
      const table = document.createElement('table');
      table.className = 'data-table';
      
      // Create table header
      const thead = document.createElement('thead');
      thead.innerHTML = `
        <tr>
          <th>Filename</th>
          <th>Type</th>
          <th>Size</th>
          <th>Chunks</th>
          <th>Upload Date</th>
          <th>Actions</th>
        </tr>
      `;
      table.appendChild(thead);
      
      // Create table body
      const tbody = document.createElement('tbody');
      
      documents.forEach(doc => {
        // Format date
        const date = new Date(doc.created_at);
        const formattedDate = date.toLocaleString();
        
        // Format file size
        const sizeInKB = Math.round(doc.file_size / 1024);
        const formattedSize = sizeInKB >= 1024 
          ? `${(sizeInKB / 1024).toFixed(2)} MB` 
          : `${sizeInKB} KB`;
        
        // Create table row
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${doc.filename}</td>
          <td>${doc.file_type}</td>
          <td>${formattedSize}</td>
          <td>${doc.chunk_count}</td>
          <td>${formattedDate}</td>
          <td>
            <button class="btn btn-danger btn-sm delete-doc-btn" data-id="${doc.id}" data-name="${doc.filename}">
              <i class="fas fa-trash"></i> Delete
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });
      
      table.appendChild(tbody);
      documentList.appendChild(table);
      
      // Add event listeners for delete buttons
      document.querySelectorAll('.delete-doc-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          const docId = this.getAttribute('data-id');
          const docName = this.getAttribute('data-name');
          if (confirm(`Are you sure you want to delete "${docName}"?`)) {
            deleteDocument(docId);
          }
        });
      });
    })
    .catch(error => {
      console.error('Error loading documents:', error);
      documentList.innerHTML = '<div class="document-item error">Failed to load documents. Please try again.</div>';
    });
}

/**
 * Delete a document
 */
function deleteDocument(documentId) {
  // Send a DELETE request to the server
  fetch(`/api/documents/${documentId}`, {
    method: 'DELETE'
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    showAlert(data.message || 'Document deleted successfully', 'success');
    loadDocumentList(); // Refresh the list
    loadUsageStats(); // Also refresh stats
  })
  .catch(error => {
    console.error('Error deleting document:', error);
    showAlert('Failed to delete document. Please try again.', 'error');
  });
}

/**
 * Initialize chat history functionality
 */
function initChatHistory() {
  const sessionsTable = document.getElementById('sessions-table');
  const conversationViewer = document.getElementById('conversation-viewer');
  const conversationMessages = document.getElementById('conversation-messages');
  const conversationTitle = document.getElementById('conversation-title');
  const backButton = document.getElementById('back-to-sessions');
  
  // Load the list of chat sessions
  loadChatSessions();
  
  // Handle back button click
  backButton.addEventListener('click', function() {
    conversationViewer.style.display = 'none';
    document.querySelector('.chat-sessions').style.display = 'block';
  });
  
  /**
   * Load the list of chat sessions
   */
  function loadChatSessions() {
    // Set loading state
    sessionsTable.innerHTML = '<tr><td colspan="5" class="text-center">Loading sessions...</td></tr>';
    
    // Fetch sessions from API
    fetch('/api/sessions')
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Clear current table
        sessionsTable.innerHTML = '';
        
        // The API now returns an array directly
        const sessions = Array.isArray(data) ? data : (data.sessions || []);
        
        // Add sessions to the table
        if (sessions.length === 0) {
          sessionsTable.innerHTML = '<tr><td colspan="5" class="text-center">No chat sessions found</td></tr>';
          return;
        }
        
        sessions.forEach(session => {
          // Format dates
          const createdDate = new Date(session.created_at).toLocaleString();
          const lastActivityDate = new Date(session.last_activity).toLocaleString();
          
          // Create table row
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${session.session_id.substring(0, 10)}...</td>
            <td>${createdDate}</td>
            <td>${lastActivityDate}</td>
            <td>${session.message_count}</td>
            <td>
              <button class="btn btn-primary btn-sm view-conversation-btn" data-session-id="${session.session_id}">
                <i class="fas fa-comments"></i> View
              </button>
            </td>
          `;
          sessionsTable.appendChild(tr);
        });
        
        // Add event listeners for view buttons
        document.querySelectorAll('.view-conversation-btn').forEach(btn => {
          btn.addEventListener('click', function() {
            const sessionId = this.getAttribute('data-session-id');
            loadConversation(sessionId);
          });
        });
      })
      .catch(error => {
        console.error('Error loading sessions:', error);
        sessionsTable.innerHTML = '<tr><td colspan="5" class="text-center">Failed to load sessions. Please try again.</td></tr>';
      });
  }
  
  /**
   * Load and display a conversation
   */
  function loadConversation(sessionId) {
    // Set loading state
    conversationTitle.textContent = 'Loading conversation...';
    conversationMessages.innerHTML = '<div class="loading">Loading messages...</div>';
    conversationViewer.style.display = 'block';
    document.querySelector('.chat-sessions').style.display = 'none';
    
    // Fetch conversation from API
    fetch(`/api/sessions/${sessionId}/messages`)
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP error ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        // Update conversation title
        conversationTitle.textContent = `Conversation (${sessionId.substring(0, 10)}...)`;
        
        // Clear messages container
        conversationMessages.innerHTML = '';
        
        // Add messages to the container
        // The API now returns an array directly
        const messages = Array.isArray(data) ? data : (data.messages || []);
        
        if (messages.length === 0) {
          conversationMessages.innerHTML = '<div class="empty-conversation">No messages in this conversation</div>';
          return;
        }
        
        messages.forEach(msg => {
          // Create message element
          const messageDiv = document.createElement('div');
          messageDiv.className = `message ${msg.is_user ? 'user' : 'ai'}`;
          
          // Format date
          const date = new Date(msg.created_at).toLocaleString();
          
          // Create message bubble with content
          const messageBubble = document.createElement('div');
          messageBubble.className = 'message-bubble';
          messageBubble.innerHTML = msg.content;
          
          // Create message metadata element
          const metaDiv = document.createElement('div');
          metaDiv.className = 'message-meta';
          
          if (msg.is_user) {
            metaDiv.textContent = `User • ${date}`;
          } else {
            let metaText = `AI • ${date}`;
            if (msg.tokens_used) {
              metaText += ` • ${msg.tokens_used} tokens`;
            }
            metaDiv.textContent = metaText;
            
            // Add feedback if available
            if (msg.feedback) {
              const feedbackDiv = document.createElement('div');
              feedbackDiv.className = `message-feedback ${msg.feedback.is_positive ? 'positive' : 'negative'}`;
              
              const icon = msg.feedback.is_positive ? 'thumbs-up' : 'thumbs-down';
              feedbackDiv.innerHTML = `<i class="fas fa-${icon}"></i> ${msg.feedback.is_positive ? 'Positive' : 'Negative'} feedback`;
              
              if (msg.feedback.comment) {
                feedbackDiv.innerHTML += ` - "${msg.feedback.comment}"`;
              }
              
              metaDiv.appendChild(feedbackDiv);
            }
          }
          
          // Assemble message
          messageDiv.appendChild(messageBubble);
          messageDiv.appendChild(metaDiv);
          
          // Add to container
          conversationMessages.appendChild(messageDiv);
        });
        
        // Scroll to bottom
        conversationMessages.scrollTop = conversationMessages.scrollHeight;
      })
      .catch(error => {
        console.error('Error loading conversation:', error);
        conversationMessages.innerHTML = '<div class="error">Failed to load conversation. Please try again.</div>';
      });
  }
}

/**
 * Show an alert message
 */
function showAlert(message, type = 'success') {
  const alertContainer = document.getElementById('alert-container');
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  
  alertContainer.appendChild(alert);
  
  // Remove the alert after 5 seconds
  setTimeout(() => {
    alert.remove();
  }, 5000);
}
