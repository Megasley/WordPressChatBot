# This file is now a wrapper that imports from main.py
# This solves the circular import issue

from main import app

# This file is kept for backward compatibility
# All routes and functionality have been moved to main.py

# @app.route('/api/feedback', methods=['POST'])
# def submit_feedback():
#     try:
#         data = request.json
#         session_id = data.get('session_id')
#         message_index = data.get('message_index')
#         feedback_type = data.get('feedback')  # 'positive' or 'negative'
#         comment = data.get('comment', '')
        
#         # Find the session
#         chat_session = ChatSession.query.filter_by(session_id=session_id).first()
#         if not chat_session:
#             return jsonify({'error': 'Session not found'}), 404
        
#         # Find the AI message (is_user=False)
#         message = ChatMessage.query.filter_by(
#             session_id=chat_session.id,
#             message_index=message_index,
#             is_user=False
#         ).first()
        
#         if not message:
#             return jsonify({'error': 'Message not found'}), 404
        
#         # Store the feedback
#         is_positive = (feedback_type == 'positive')
#         feedback_entry = MessageFeedback(
#             message_id=message.id,
#             is_positive=is_positive,
#             comment=comment if comment else None
#         )
        
#         db.session.add(feedback_entry)
#         db.session.commit()
        
#         logger.info(f"Feedback received for session {session_id}, message {message_index}: {feedback_type}")
        
#         return jsonify({'message': 'Feedback recorded'})
    
#     except Exception as e:
#         logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/api/regenerate', methods=['POST'])
# def regenerate_response():
#     try:
#         data = request.json
#         session_id = data.get('session_id')
#         message_index = int(data.get('message_index'))
        
#         # Find the session
#         chat_session = ChatSession.query.filter_by(session_id=session_id).first()
#         if not chat_session:
#             return jsonify({'error': 'Session not found'}), 404
        
#         # Find the original user message
#         user_message = ChatMessage.query.filter_by(
#             session_id=chat_session.id,
#             message_index=message_index,
#             is_user=True
#         ).first()
        
#         if not user_message:
#             return jsonify({'error': 'Original message not found'}), 404
        
#         original_message = user_message.content
        
#         # Find the AI message to regenerate
#         ai_message = ChatMessage.query.filter_by(
#             session_id=chat_session.id,
#             message_index=message_index,
#             is_user=False
#         ).first()
        
#         if not ai_message:
#             return jsonify({'error': 'AI message not found'}), 404
        
#         # Get recent conversation history (excluding the message to regenerate)
#         if message_index > 0:
#             recent_messages = ChatMessage.query.filter(
#                 ChatMessage.session_id == chat_session.id,
#                 ChatMessage.message_index < message_index
#             ).order_by(ChatMessage.message_index.desc()).limit(4).all()  # Get 4 to get 2 exchanges
            
#             conversation_history = []
#             for msg in reversed(recent_messages):
#                 if msg.is_user:
#                     conversation_history.append({'user': msg.content})
#                 else:
#                     conversation_history.append({'ai': msg.content})
#         else:
#             conversation_history = []
        
#         # Embed the query
#         query_embedding = embed_query(original_message)
        
#         # Search for relevant context in vector store
#         relevant_contexts = vector_store.search(query_embedding, top_k=3)
        
#         # Generate new response
#         ai_response, tokens_used = generate_response(
#             original_message, 
#             relevant_contexts, 
#             conversation_history
#         )
        
#         # Update AI message in the database
#         ai_message.content = ai_response
#         ai_message.tokens_used = tokens_used
#         ai_message.created_at = datetime.now()
        
#         # Update last activity timestamp
#         chat_session.last_activity = datetime.now()
        
#         # Update API usage statistics
#         today = datetime.now().date()
#         api_usage = ApiUsage.query.filter_by(date=today).first()
#         if api_usage:
#             api_usage.api_calls += 1
#             api_usage.tokens_used += tokens_used
        
#         # Commit all changes
#         db.session.commit()
        
#         timestamp = datetime.now().isoformat()
#         return jsonify({
#             'message': ai_response,
#             'timestamp': timestamp
#         })
    
#     except Exception as e:
#         logger.error(f"Error regenerating response: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/api/documents/<int:document_id>', methods=['DELETE'])
# def delete_document(document_id):
#     try:
#         # Find the document
#         document = DocumentUpload.query.get(document_id)
#         if not document:
#             return jsonify({'error': 'Document not found'}), 404
        
#         # Delete from database
#         db.session.delete(document)
#         db.session.commit()
        
#         # Note: In a real implementation, we would also need to remove it from the vector store
#         # This would require modifying the vector store to support document deletion
        
#         return jsonify({'message': f'Document {document.original_filename} deleted successfully'})
    
#     except Exception as e:
#         logger.error(f"Error deleting document: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500
        
# @app.route('/api/documents', methods=['GET'])
# def get_documents():
#     try:
#         documents = DocumentUpload.query.order_by(DocumentUpload.created_at.desc()).all()
        
#         # Convert to JSON-serializable format
#         docs_list = []
#         for doc in documents:
#             docs_list.append({
#                 'id': doc.id,
#                 'filename': doc.original_filename,
#                 'file_type': doc.file_type,
#                 'file_size': doc.file_size,
#                 'chunk_count': doc.chunk_count,
#                 'created_at': doc.created_at.isoformat(),
#                 'indexed': doc.indexed
#             })
        
#         return jsonify({'documents': docs_list})
    
#     except Exception as e:
#         logger.error(f"Error getting documents: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/api/sessions', methods=['GET'])
# def get_sessions():
#     try:
#         # Get all chat sessions, ordered by last activity
#         sessions = ChatSession.query.order_by(ChatSession.last_activity.desc()).all()
        
#         # Convert to JSON-serializable format
#         sessions_list = []
#         for session in sessions:
#             # Count messages in this session
#             message_count = ChatMessage.query.filter_by(session_id=session.id).count()
            
#             sessions_list.append({
#                 'id': session.id,
#                 'session_id': session.session_id,
#                 'created_at': session.created_at.isoformat(),
#                 'last_activity': session.last_activity.isoformat(),
#                 'ip_address': session.ip_address,
#                 'user_agent': session.user_agent,
#                 'message_count': message_count
#             })
        
#         return jsonify({'sessions': sessions_list})
    
#     except Exception as e:
#         logger.error(f"Error getting sessions: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/api/sessions/<session_id>/messages', methods=['GET'])
# def get_session_messages(session_id):
#     try:
#         # Find the session
#         session = ChatSession.query.filter_by(session_id=session_id).first()
#         if not session:
#             return jsonify({'error': 'Session not found'}), 404
        
#         # Get all messages for this session
#         messages = ChatMessage.query.filter_by(
#             session_id=session.id
#         ).order_by(ChatMessage.message_index).all()
        
#         # Convert to JSON-serializable format
#         messages_list = []
#         for msg in messages:
#             # Get feedback for AI messages
#             feedback = None
#             if not msg.is_user:
#                 feedback_entry = MessageFeedback.query.filter_by(message_id=msg.id).first()
#                 if feedback_entry:
#                     feedback = {
#                         'is_positive': feedback_entry.is_positive,
#                         'comment': feedback_entry.comment,
#                         'created_at': feedback_entry.created_at.isoformat()
#                     }
            
#             messages_list.append({
#                 'id': msg.id,
#                 'message_index': msg.message_index,
#                 'is_user': msg.is_user,
#                 'content': msg.content,
#                 'created_at': msg.created_at.isoformat(),
#                 'tokens_used': msg.tokens_used,
#                 'feedback': feedback
#             })
        
#         # Session details
#         session_details = {
#             'id': session.id,
#             'session_id': session.session_id,
#             'created_at': session.created_at.isoformat(),
#             'last_activity': session.last_activity.isoformat(),
#             'ip_address': session.ip_address,
#             'user_agent': session.user_agent
#         }
        
#         return jsonify({
#             'session': session_details,
#             'messages': messages_list
#         })
    
#     except Exception as e:
#         logger.error(f"Error getting session messages: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/api/stats', methods=['GET'])
# def get_stats():
#     try:
#         # Get usage statistics
#         total_sessions = ChatSession.query.count()
#         total_messages = ChatMessage.query.count()
#         ai_messages = ChatMessage.query.filter_by(is_user=False).count()
#         user_messages = ChatMessage.query.filter_by(is_user=True).count()
        
#         # Get API usage totals
#         api_usage = ApiUsage.query.all()
#         total_api_calls = sum(usage.api_calls for usage in api_usage)
#         total_tokens = sum(usage.tokens_used for usage in api_usage)
        
#         # Get feedback statistics
#         positive_feedback = MessageFeedback.query.filter_by(is_positive=True).count()
#         negative_feedback = MessageFeedback.query.filter_by(is_positive=False).count()
        
#         # Calculate positive feedback percentage
#         if positive_feedback + negative_feedback > 0:
#             positive_percentage = round((positive_feedback / (positive_feedback + negative_feedback)) * 100)
#         else:
#             positive_percentage = 0
        
#         # Build response
#         response = {
#             'total_sessions': total_sessions,
#             'total_messages': total_messages,
#             'ai_messages': ai_messages,
#             'user_messages': user_messages,
#             'total_api_calls': total_api_calls,
#             'total_tokens': total_tokens,
#             'positive_feedback': positive_feedback,
#             'negative_feedback': negative_feedback,
#             'positive_percentage': positive_percentage,
#             'document_count': DocumentUpload.query.count()
#         }
        
#         return jsonify(response)
    
#     except Exception as e:
#         logger.error(f"Error getting stats: {str(e)}", exc_info=True)
#         return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# @app.route('/widget.js')
# def serve_widget_js():
#     host_url = request.host_url.rstrip('/')
#     try:
#         with open('static/js/chat_widget.js', 'r') as f:
#             js_content = f.read().replace('{{HOST_URL}}', host_url)
        
#         return app.response_class(
#             response=js_content,
#             status=200,
#             mimetype='application/javascript'
#         )
#     except Exception as e:
#         logger.error(f"Error serving widget.js: {str(e)}", exc_info=True)
#         return f"console.error('Error loading widget: {str(e)}');", 500, {'Content-Type': 'application/javascript'}

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)
