// File: src/api.js

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

// Fetches the list of conversations for the sidebar
export const fetchHistorySummary = async (clientSessionId) => {
  const response = await fetch(`${API_BASE_URL}/history/summary_list?client_session_id=${clientSessionId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch history summary');
  }
  return response.json();
};

// Fetches the full message history for a single conversation
export const fetchConversation = async (conversationId) => {
  const response = await fetch(`${API_BASE_URL}/history/conversation_by_id?conversation_id=${conversationId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch conversation messages');
  }
  return response.json();
};

// Handles file uploads
export const uploadFile = async (clientSessionId, file) => {
    const formData = new FormData();
    formData.append('session_id', clientSessionId);
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/upload_for_agent`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'File upload failed');
    }
    return response.json();
};

// Clears the file context on the server
export const clearFileContext = async (clientSessionId) => {
    const response = await fetch(`${API_BASE_URL}/clear_file_context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_session_id: clientSessionId }),
    });
     if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to clear context');
    }
    return response.json();
};

// Handles the main chat streaming logic
export const chatStream = async (payload, onData, signal) => {
  const response = await fetch(`${API_BASE_URL}/chat_stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal, // For aborting the request
  });

  if (!response.ok || !response.body) {
    throw new Error("Failed to connect to the chat stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n\n').filter(line => line.trim().startsWith('data:'));

    for (const line of lines) {
        try {
          const jsonData = JSON.parse(line.substring(6));
          onData(jsonData);
        } catch (error) {
          console.error('Error parsing stream data:', error, 'Raw line:', line);
        }
    }
  }
};