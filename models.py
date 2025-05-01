from datetime import datetime
from extensions import db


class ChatSession(db.Model):
    """
    A chat session represents a conversation between a user and the AI.
    Each session has a unique session_id and can contain multiple messages.
    """
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(255), nullable=True)
    
    # Relationship: One session has many messages
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<ChatSession {self.session_id}>'


class ChatMessage(db.Model):
    """
    A chat message represents a single exchange in a conversation.
    Each message belongs to a session and can be either from the user or the AI.
    """
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)
    message_index = db.Column(db.Integer, nullable=False)  # Position in the conversation
    is_user = db.Column(db.Boolean, default=True)  # True if message is from user, False if from AI
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tokens_used = db.Column(db.Integer, nullable=True)  # Only for AI messages
    
    # Relationship: One message can have many feedbacks
    feedbacks = db.relationship('MessageFeedback', backref='message', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        sender = "User" if self.is_user else "AI"
        return f'<ChatMessage #{self.message_index} from {sender}>'
    

class MessageFeedback(db.Model):
    """
    Feedback for AI messages provided by users.
    This allows tracking of positive/negative feedback for each AI response.
    """
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey('chat_message.id'), nullable=False)
    is_positive = db.Column(db.Boolean, nullable=False)  # True for positive, False for negative
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=True)  # Optional comment
    
    def __repr__(self):
        feedback_type = "Positive" if self.is_positive else "Negative"
        return f'<MessageFeedback {feedback_type}>'


class DocumentUpload(db.Model):
    """
    Tracks uploaded documents used for context in AI responses.
    """
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(64), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # In bytes
    chunk_count = db.Column(db.Integer, nullable=False, default=0)  # Number of chunks created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    indexed = db.Column(db.Boolean, default=False)  # Whether document has been indexed
    
    def __repr__(self):
        return f'<DocumentUpload {self.original_filename}>'


class ApiUsage(db.Model):
    """
    Tracks API usage for analytics and rate limiting.
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    api_calls = db.Column(db.Integer, default=0)
    tokens_used = db.Column(db.Integer, default=0)
    unique_sessions = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ApiUsage {self.date}: {self.api_calls} calls, {self.tokens_used} tokens>'