/**
 * WordPress AI Chatbot Widget Installation Script
 * Copy this entire file and save it as 'wp-ai-chatbot.js' in your WordPress theme.
 * Then include it using wp_enqueue_script or by adding a script tag to your footer.
 */

(function() {
  // Load the chatbot widget from your server
  const script = document.createElement('script');
  
  // Replace this URL with your actual backend server URL
  script.src = 'https://your-backend-server.com/widget.js';
  
  script.async = true;
  document.body.appendChild(script);
})();
