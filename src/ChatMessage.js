// // File: src/ChatMessage.js
// // Final, corrected version.

// import React from 'react';
// import { marked } from 'marked';

// const ChatMessage = ({ msg }) => {
//   const isUser = msg.role === 'user';
//   const messageClass = isUser ? 'user' : 'assistant';
  
//   // This function now correctly uses msg.text
//   const createMarkup = () => {
//     let combinedContent = '';
//     // Use msg.text for the main content
//     if (msg.text) {
//       combinedContent += marked.parse(msg.text);
//     }
//     // Append any additional HTML content (like plots)
//     if (msg.htmlContent) {
//       combinedContent += msg.htmlContent;
//     }
//     return { __html: combinedContent };
//   };

//   return (
//     <div className={`message ${messageClass}`}>
//       <div className="message-content" dangerouslySetInnerHTML={createMarkup()} />
//     </div>
//   );
// };

// export default ChatMessage;