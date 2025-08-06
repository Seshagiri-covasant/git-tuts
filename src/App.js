import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import Sidebar from './Sidebar';
import * as api from './api';
import ChatMessage from './ChatMessage';

const MCP_SERVER_PLOT_URL = process.env.REACT_APP_MCP_SERVER_URL;

function App() {
  const [clientSessionId, setClientSessionId] = useState('');
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatHistoryList, setChatHistoryList] = useState([]);
  const [activeChatTitle, setActiveChatTitle] = useState('New Chat');
  const [inputValue, setInputValue] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const chatWindowRef = useRef(null);
  const abortControllerRef = useRef(null);
  const [streamingAnswer, setStreamingAnswer] = useState('');
  const [assistantMsgId, setAssistantMsgId] = useState(null);

  const fetchHistory = useCallback(async (currentClientId) => {
    if (!currentClientId) return [];
    setIsLoadingHistory(true);
    try {
      const data = await api.fetchHistorySummary(currentClientId);
      setChatHistoryList(data || []);
      return data || [];
    } catch (error) {
      console.error("Failed to fetch history:", error);
      setChatHistoryList([]);
      return [];
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const startNewChat = useCallback(() => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setActiveConversationId(null);
    setMessages([]);
    setActiveChatTitle('New Chat');
    setInputValue('');
    localStorage.removeItem('activeChatInfo');
  }, []);

  const loadConversation = useCallback(async (convId, title) => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setIsLoadingHistory(true);
    setMessages([]);
    try {
      const data = await api.fetchConversation(convId);
      const processed = (data.messages || []).map(msg => ({ ...msg, text: msg.content }));
      setMessages(processed);
      setActiveConversationId(convId);
      setActiveChatTitle(title || "Chat History");
      localStorage.setItem('activeChatInfo', JSON.stringify({ id: convId, title }));
    } catch (error) {
      console.error("Error loading conversation:", error);
      startNewChat();
    } finally {
      setIsLoadingHistory(false);
    }
  }, [startNewChat]);

  useEffect(() => {
    const storedClientId = localStorage.getItem('chatClientSessionId') || `client-${crypto.randomUUID()}`;
    localStorage.setItem('chatClientSessionId', storedClientId);
    setClientSessionId(storedClientId);

    const lastChatInfo = localStorage.getItem('activeChatInfo');
    let loaded = false;
    if (lastChatInfo) {
      try {
        const { id, title } = JSON.parse(lastChatInfo);
        if (id) {
          loadConversation(id, title);
          loaded = true;
        }
      } catch (e) { }
    }

    if (!loaded) {
      // no last chat to load
    }

    fetchHistory(storedClientId);
  }, [fetchHistory, loadConversation]);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTo(0, chatWindowRef.current.scrollHeight);
    }
  }, [messages]);

  useEffect(() => {
    if (streamingAnswer && assistantMsgId) {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === assistantMsgId
            ? { ...msg, text: streamingAnswer }
            : msg
        )
      );
    }
  }, [streamingAnswer,assistantMsgId]);

  const handleSendMessage = async () => {
    if (inputValue.trim() === '' || isStreaming) return;

    const userMessageText = inputValue;
    const userMsgId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();

    setMessages(prev => [
      ...prev,
      { id: userMsgId, role: 'user', text: userMessageText },
      { id: assistantId, role: 'assistant', text: '' }
    ]);

    setInputValue('');
    setIsStreaming(true);
    setStreamingAnswer('');
    setAssistantMsgId(assistantId);
    abortControllerRef.current = new AbortController();

    const payload = {
      client_session_id: clientSessionId,
      message: userMessageText,
      conversation_id: activeConversationId,
    };

    const handleStreamData = (data) => {
      console.log("Stream event:", data); // ✅ Debug stream

      if (data.type === 'new_session_id') {
        const newConvId = data.conversation_id;
        setActiveConversationId(newConvId);
      } else if (data.type === 'llm_token') {
        setStreamingAnswer(prev => prev + data.content);
      } else if (data.status === 'completed' && data.data?.thumbnail_base64) {
        const plotHtml = `<img src="data:image/png;base64,${data.data.thumbnail_base64}" alt="Plot" style="max-width: 200px; border-radius: 8px;" /><br/><a href="${MCP_SERVER_PLOT_URL}/plots/${data.data.plot_file_path}" target="_blank" rel="noopener noreferrer">View Full Plot</a>`;
        setMessages(prev => prev.map(msg => msg.id === assistantId ? { ...msg, htmlContent: (msg.htmlContent || '') + plotHtml } : msg));
      } else if (data.type === 'error') {
        setMessages(prev => prev.map(msg => msg.id === assistantId ? { ...msg, text: `Error: ${data.content}` } : msg));
      }
    };

    try {
      await api.chatStream(payload, handleStreamData, abortControllerRef.current.signal);
    } catch (error) {
      if (error.name !== 'AbortError') {
        setMessages(prev => prev.map(msg => msg.id === assistantId ? { ...msg, text: `Error: ${error.message}` } : msg));
      }
    } finally {
      setIsStreaming(false);
      fetchHistory(clientSessionId);
    }
  };

  useEffect(() => {
    if (activeConversationId) {
      const activeChat = chatHistoryList.find(c => c.id === activeConversationId);
      if (activeChat) {
        setActiveChatTitle(activeChat.title);
        localStorage.setItem('activeChatInfo', JSON.stringify({ id: activeChat.id, title: activeChat.title }));
      }
    } else {
      setActiveChatTitle('New Chat');
    }
  }, [activeConversationId, chatHistoryList]);

  return (
    <div className="App-container">
      <Sidebar
        history={chatHistoryList}
        loadConversation={loadConversation}
        isLoadingHistory={isLoadingHistory}
        startNewChat={startNewChat}
        activeConversationId={activeConversationId}
      />
      <div className="main-content-area">
        <header className="chat-header">{activeChatTitle}</header>
        <div className="chat-view-container">
          <div className="chat-window" ref={chatWindowRef}>
            {messages.map((msg) => <ChatMessage key={msg.id} msg={msg} />)}
          </div>
          <div className="input-area-wrapper">
            <div className="input-area">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Send a message..."
                disabled={isStreaming}
              />
              <button onClick={handleSendMessage} disabled={isStreaming || !inputValue.trim()}>Send</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;