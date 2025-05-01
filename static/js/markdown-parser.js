/**
 * Simple Markdown Parser for DeepSeek AI Chatbot
 * Handles basic markdown formatting
 */
function parseMarkdown(text) {
  if (!text) return '';
  
  // Convert line breaks
  text = text.replace(/\n/g, '<br>');
  
  // Handle headers (h1, h2, h3)
  text = text.replace(/### (.*?)(?:<br>|$)/g, '<h3>$1</h3>');
  text = text.replace(/## (.*?)(?:<br>|$)/g, '<h2>$1</h2>');
  text = text.replace(/# (.*?)(?:<br>|$)/g, '<h1>$1</h1>');
  
  // Handle bold and italic
  text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
  text = text.replace(/__(.*?)__/g, '<strong>$1</strong>');
  text = text.replace(/_(.*?)_/g, '<em>$1</em>');
  
  // Handle code blocks
  text = text.replace(/```(.*?)```/gs, function(match, p1) {
    return '<pre class="wp-ai-chatbot-code-block"><code>' + p1.trim() + '</code></pre>';
  });
  
  // Handle inline code
  text = text.replace(/`(.*?)`/g, '<code class="wp-ai-chatbot-inline-code">$1</code>');
  
  // Handle links
  text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  
  // Handle unordered lists
  text = text.replace(/^\* (.*?)(?:<br>|$)/gm, '<li>$1</li>');
  text = text.replace(/^- (.*?)(?:<br>|$)/gm, '<li>$1</li>');
  text = text.replace(/(<li>.*?<\/li>)/gs, '<ul>$1</ul>');
  
  // Handle ordered lists
  text = text.replace(/^\d+\. (.*?)(?:<br>|$)/gm, '<li>$1</li>');
  text = text.replace(/(<li>.*?<\/li>)/gs, '<ol>$1</ol>');
  
  // Deduplicate list wrappers (this is a simple fix for nested lists)
  text = text.replace(/<\/ul><ul>/g, '');
  text = text.replace(/<\/ol><ol>/g, '');
  
  return text;
}