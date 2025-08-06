// import React from 'react';
// import './Sidebar.css';

// function Sidebar({
//   history,
//   loadConversation,
//   isLoadingHistory,
//   startNewChat,
//   activeConversationId,
// //   handleFileChange,
//   isStreaming,
// // fileInputRef,
// // selectedFile,
// //   handleFileUpload,
// //   uploadStatus,
// //   handleDeleteFileContext,
// //   isFileContextActive,
// }) {
//   return (
//     <div className="sidebar">
//       <div className="sidebar-header">
//         <button className="new-chat-button" onClick={startNewChat}>
//           + New Chat
//         </button>
//       </div>

     

//       <div className="sidebar-section history-section">
//         <h3>History</h3>
//         {isLoadingHistory ? (
//           <p className="loading-text">Loading...</p>
//         ) : (
//           <ul className="history-list">
//             {history.map((chat) => (
//               <li
//                 key={chat.id}
//                 className={`history-item ${chat.id === activeConversationId ? 'active' : ''}`}
//                 onClick={() => loadConversation(chat.id, chat.title)}
//                 title={chat.title}
//               >
//                 {chat.title}
//               </li>
//             ))}
//           </ul>
//         )}
//       </div>
//     </div>
//   );
// }

// export default Sidebar;
// File: src/Sidebar.js

import React from 'react';
import './Sidebar.css';

function Sidebar({
  history,
  loadConversation,
  isLoadingHistory,
  startNewChat,
  activeConversationId,
  handleFileChange,
  isStreaming,
  fileInputRef,
  selectedFile,
  handleFileUpload,
  uploadStatus,
  handleDeleteFileContext,
  isFileContextActive,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <button className="new-chat-button" onClick={startNewChat}>
          + New Chat
        </button>
      </div>

      <div className="sidebar-section file-upload-section">
        <h3>File Upload</h3>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          disabled={isStreaming}
        />
        <div className="file-buttons">
            <button
              onClick={handleFileUpload}
              disabled={!selectedFile || isStreaming}
              className="upload-btn"
            >
              Upload
            </button>
            {isFileContextActive && (
                 <button 
                    onClick={handleDeleteFileContext} 
                    disabled={isStreaming} 
                    className="clear-btn"
                >
                    Clear Context
                </button>
            )}
        </div>
        {uploadStatus && <p className="upload-status">{uploadStatus}</p>}
      </div>

      <div className="sidebar-section history-section">
        <h3>History</h3>
        {isLoadingHistory ? (
          <p className="loading-text">Loading...</p>
        ) : (
          <ul className="history-list">
            {history.map((chat) => (
              <li
                key={chat.id}
                className={`history-item ${chat.id === activeConversationId ? 'active' : ''}`}
                onClick={() => loadConversation(chat.id, chat.title)}
                title={chat.title}
              >
                {chat.title}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Sidebar;