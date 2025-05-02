import os
import logging
import json
import time
from datetime import datetime
from typing import List, Dict

from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from flask_migrate import Migrate
from extensions import db
from dotenv import load_dotenv


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)

# Setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Configure the database connection
# app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot.db")
# app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
#     "pool_size": 20,  # Increased pool size
#     "max_overflow": 30,  # Allow more connections when needed
#     "pool_timeout": 30,  # Timeout for getting a connection
#     "pool_recycle": 300,  # Recycle connections after 5 minutes
#     "pool_pre_ping": True,  # Check connection health before use
# }

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 1800,        # Recycle every 30 mins
    "pool_pre_ping": True        # 👈 Prevents using dead connections
}


# Initialize the app with the extension
db.init_app(app)

migrate = Migrate(app, db)

# Apply CORS to the app
# from flask_cors import CORS
CORS(app, origins=["https://bitcoiners.africa"])

# Create all database tables
with app.app_context():
    from models import ChatSession, ChatMessage, MessageFeedback, ApiUsage, DocumentUpload
    db.create_all()

# Import utility modules
from utils.vectorstore import VectorStore
from utils.embedding import embed_query
from utils.deepseek_api import generate_response
from utils.rate_limiter import RateLimiter

# Initialize vector store
vector_store = VectorStore()

# Initialize rate limiter (100 queries per day per IP)
rate_limiter = RateLimiter(max_requests=100, time_window=86400)  # 24 hours in seconds

# In-memory cache for active sessions (to reduce database queries)
active_sessions_cache = {}
# Cache for conversation history
conversation_cache = {}
# Cache TTL in seconds
CACHE_TTL = 300  # 5 minutes

def get_cached_conversation(session_id: str) -> List[Dict[str, str]]:
    """Get conversation history from cache or database"""
    current_time = time.time()
    
    # Check cache first
    if session_id in conversation_cache:
        cache_time, history = conversation_cache[session_id]
        if current_time - cache_time < CACHE_TTL:
            return history
    
    # If not in cache or expired, get from database
    chat_session = ChatSession.query.filter_by(session_id=session_id).first()
    if not chat_session:
        return []
    
    history = []
    previous_messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.message_index).all()
    
    for msg in previous_messages:
        if msg.is_user:
            history.append({'user': msg.content})
        else:
            history.append({'ai': msg.content})
    
    # Update cache
    conversation_cache[session_id] = (current_time, history)
    return history

# Define routes
@app.route('/')
def home():
    """Main landing page with chatbot widget"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Testing page for development"""
    return render_template('test.html')

@app.route('/admin')
def admin():
    # Get usage statistics
    total_sessions = ChatSession.query.count()
    total_messages = ChatMessage.query.count()
    ai_messages = ChatMessage.query.filter_by(is_user=False).count()
    user_messages = ChatMessage.query.filter_by(is_user=True).count()
    
    # Get API usage by date
    api_usage = ApiUsage.query.order_by(ApiUsage.date.desc()).all()
    
    # Get document list
    documents = DocumentUpload.query.order_by(DocumentUpload.created_at.desc()).all()
    
    # Get feedback statistics
    positive_feedback = MessageFeedback.query.filter_by(is_positive=True).count()
    negative_feedback = MessageFeedback.query.filter_by(is_positive=False).count()
    
    # Pass statistics to the template
    return render_template('admin.html', 
                          stats={
                              'total_sessions': total_sessions,
                              'total_messages': total_messages,
                              'ai_messages': ai_messages,
                              'user_messages': user_messages,
                              'positive_feedback': positive_feedback,
                              'negative_feedback': negative_feedback
                          },
                          api_usage=api_usage,
                          documents=documents)

@app.route('/api/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        query = data.get('query', '').strip()
        session_id = data.get('session_id', '')
        ip_address = request.remote_addr
        user_agent = request.user_agent.string
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Get conversation history from cache
        conversation_history = get_cached_conversation(session_id)
        
        # Get message index
        next_index = len(conversation_history)
        
        # Generate embeddings for the query
        query_embedding = embed_query(query)
        
        # Search for relevant chunks
        relevant_chunks = vector_store.search(query_embedding)
        
        # Generate response using DeepSeek API
        response_text, tokens_used = generate_response(query, relevant_chunks, conversation_history)
        
        # Get or create session
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            chat_session = ChatSession(
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.session.add(chat_session)
            db.session.commit()
        else:
            # Update last activity
            chat_session.last_activity = datetime.utcnow()
            db.session.commit()
        
        # Create messages in a single transaction
        with db.session.begin():
            # Create user message
            user_message = ChatMessage(
                session_id=chat_session.id,
                message_index=next_index,
                is_user=True,
                content=query
            )
            db.session.add(user_message)
            
            # Create AI message
            ai_message = ChatMessage(
                session_id=chat_session.id,
                message_index=next_index + 1,
                is_user=False,
                content=response_text,
                tokens_used=tokens_used
            )
            db.session.add(ai_message)
        
        # Update cache
        conversation_history.extend([
            {'user': query},
            {'ai': response_text}
        ])
        conversation_cache[session_id] = (time.time(), conversation_history)
        
        return jsonify({
            'response': response_text,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file and (file.filename.endswith('.txt') or file.filename.endswith('.md')):
            # Read file content
            content = file.read().decode('utf-8')
            file_size = len(content.encode('utf-8'))
            file_type = file.filename.split('.')[-1]
            
            # Generate a unique filename for storage
            stored_filename = f"{uuid.uuid4().hex}.{file_type}"
            
            # Process and add to vector store
            success = vector_store.add_document(content, file.filename)
            
            if success:
                # Store document information in the database
                document = DocumentUpload(
                    filename=stored_filename,
                    original_filename=file.filename,
                    file_type=file_type,
                    file_size=file_size,
                    chunk_count=len(content) // 500 + 1,  # Rough estimate based on 500 char chunks
                    indexed=True
                )
                db.session.add(document)
                db.session.commit()
                
                return jsonify({
                    'message': f'Successfully processed and added {file.filename} to knowledge base',
                    'document_id': document.id
                })
            else:
                return jsonify({'error': 'Failed to process document'}), 500
        else:
            return jsonify({'error': 'Invalid file type. Only .txt and .md files are supported'}), 400
    
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        session_id = data.get('session_id')
        message_index = data.get('message_index')
        feedback_type = data.get('feedback')  # 'positive' or 'negative'
        comment = data.get('comment', '')
        
        # Find the session
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Find the AI message (is_user=False)
        message = ChatMessage.query.filter_by(
            session_id=chat_session.id,
            message_index=message_index,
            is_user=False
        ).first()
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Store the feedback
        is_positive = (feedback_type == 'positive')
        feedback_entry = MessageFeedback(
            message_id=message.id,
            is_positive=is_positive,
            comment=comment if comment else None
        )
        
        db.session.add(feedback_entry)
        db.session.commit()
        
        logger.info(f"Feedback received for session {session_id}, message {message_index}: {feedback_type}")
        
        return jsonify({'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/regenerate', methods=['POST'])
def regenerate_response():
    try:
        data = request.json
        session_id = data.get('session_id')
        message_index = data.get('message_index')
        
        # Find the session
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all messages up to the user message before the AI message to regenerate
        all_messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.message_index).all()
        
        # Ensure message_index is valid (should be an AI message)
        valid_indices = [msg.message_index for msg in all_messages if not msg.is_user]
        if message_index not in valid_indices:
            return jsonify({'error': 'Invalid message index'}), 400
        
        # Get the user message that prompted this AI response
        user_message = None
        for msg in all_messages:
            if msg.message_index == message_index - 1 and msg.is_user:
                user_message = msg
                break
        
        if not user_message:
            return jsonify({'error': 'Could not find corresponding user message'}), 404
            
        # Build conversation history up to this point
        conversation_history = []
        for msg in all_messages:
            if msg.message_index < message_index - 1:  # Only include messages before this exchange
                conversation_history.append({
                    'role': 'user' if msg.is_user else 'assistant',
                    'content': msg.content
                })
                
        # Generate embeddings for the query
        query_embedding = embed_query(user_message.content)
        
        # Search for relevant chunks
        relevant_chunks = vector_store.search(query_embedding)
        
        # Generate new response using DeepSeek API
        response_text, tokens_used = generate_response(
            user_message.content, relevant_chunks, conversation_history
        )
        
        # Update the AI message in the database
        ai_message = ChatMessage.query.filter_by(
            session_id=chat_session.id,
            message_index=message_index
        ).first()
        
        ai_message.content = response_text
        ai_message.tokens_used = tokens_used
        ai_message.created_at = datetime.utcnow()  # Update timestamp
        
        db.session.commit()
        
        # Update API usage statistics
        today = datetime.utcnow().date()
        api_usage = ApiUsage.query.filter_by(date=today).first()
        
        if api_usage:
            api_usage.api_calls += 1
            api_usage.tokens_used += tokens_used
        else:
            api_usage = ApiUsage(
                date=today,
                api_calls=1,
                tokens_used=tokens_used,
                unique_sessions=1
            )
            db.session.add(api_usage)
        
        db.session.commit()
        
        # Create timestamp for response
        timestamp = datetime.utcnow().isoformat()
        
        return jsonify({
            'response': response_text,  # Keep this for backward compatibility
            'message': response_text,   # Add this for the chat widget
            'message_index': message_index,
            'timestamp': timestamp
        })
        
    except Exception as e:
        logger.error(f"Error regenerating response: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/documents/<int:document_id>', methods=['DELETE'])
def delete_document(document_id):
    try:
        document = DocumentUpload.query.get(document_id)
        if not document:
            return jsonify({'error': 'Document not found'}), 404
            
        # Delete the document
        db.session.delete(document)
        db.session.commit()
        
        # Note: For a full implementation, you would also remove the document from the vector store
        # This is not needed for this demo since we're using a simplified vector store
        
        return jsonify({'message': f'Document {document.original_filename} deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/documents', methods=['GET'])
def get_documents():
    try:
        documents = DocumentUpload.query.order_by(DocumentUpload.created_at.desc()).all()
        
        document_list = [{
            'id': doc.id,
            'filename': doc.original_filename,
            'type': doc.file_type,
            'size': doc.file_size,
            'chunks': doc.chunk_count,
            'created_at': doc.created_at.isoformat()
        } for doc in documents]
        
        return jsonify(document_list)
        
    except Exception as e:
        logger.error(f"Error getting documents: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    try:
        sessions = ChatSession.query.order_by(ChatSession.last_activity.desc()).limit(50).all()
        
        session_list = [{
            'id': session.session_id,
            'created_at': session.created_at.isoformat(),
            'last_activity': session.last_activity.isoformat(),
            'message_count': len(session.messages)
        } for session in sessions]
        
        return jsonify(session_list)
        
    except Exception as e:
        logger.error(f"Error getting sessions: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/sessions/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    try:
        chat_session = ChatSession.query.filter_by(session_id=session_id).first()
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
            
        messages = ChatMessage.query.filter_by(session_id=chat_session.id).order_by(ChatMessage.message_index).all()
        
        message_list = [{
            'index': msg.message_index,
            'is_user': msg.is_user,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'tokens_used': msg.tokens_used
        } for msg in messages]
        
        return jsonify(message_list)
        
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        # Get basic statistics
        total_sessions = ChatSession.query.count()
        total_messages = ChatMessage.query.count()
        ai_messages = ChatMessage.query.filter_by(is_user=False).count()
        user_messages = ChatMessage.query.filter_by(is_user=True).count()
        
        # Get feedback statistics
        positive_feedback = MessageFeedback.query.filter_by(is_positive=True).count()
        negative_feedback = MessageFeedback.query.filter_by(is_positive=False).count()
        
        # Get API usage by day (last 30 days)
        api_usage = ApiUsage.query.order_by(ApiUsage.date.desc()).limit(30).all()
        usage_data = [{
            'date': usage.date.isoformat(),
            'api_calls': usage.api_calls,
            'tokens_used': usage.tokens_used,
            'unique_sessions': usage.unique_sessions
        } for usage in api_usage]
        
        # Get document statistics
        document_count = DocumentUpload.query.count()
        total_file_size = db.session.query(db.func.sum(DocumentUpload.file_size)).scalar() or 0
        
        return jsonify({
            'general': {
                'total_sessions': total_sessions,
                'total_messages': total_messages,
                'ai_messages': ai_messages,
                'user_messages': user_messages,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback
            },
            'documents': {
                'count': document_count,
                'total_size': total_file_size
            },
            'usage': usage_data
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/widget.js')
def serve_widget_js():
    return app.send_static_file('js/chat_widget.js')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
