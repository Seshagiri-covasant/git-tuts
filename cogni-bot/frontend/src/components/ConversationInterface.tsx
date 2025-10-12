import React, { useState } from 'react';
import { Conversation, Message, Chatbot } from '../types';
import { Send, Bot, User, Clock } from 'lucide-react';

interface ConversationInterfaceProps {
  selectedConversation: Conversation | null;
  selectedChatbot: Chatbot | null;
  messages: Message[];
  onSendMessage: (content: string) => void;
}

const ConversationInterface: React.FC<ConversationInterfaceProps> = ({
  selectedConversation,
  selectedChatbot,
  messages,
  onSendMessage
}) => {
  const [inputMessage, setInputMessage] = useState('');

  const handleSendMessage = () => {
    if (inputMessage.trim() && selectedConversation) {
      onSendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  if (!selectedConversation) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 h-full">
        <div className="text-center">
          <Bot className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Conversation Selected</h3>
          <p className="text-gray-500 mb-4">
            {selectedChatbot 
              ? `Select a conversation from the sidebar to start chatting with ${selectedChatbot.name}`
              : 'Please select a chatbot first, then choose a conversation to begin'
            }
          </p>
          {selectedChatbot && (
            <button className="px-4 py-2 btn-primary text-white rounded-lg transition-colors shadow-sm">
              Start New Conversation
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-800 mt-2">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
          currentConversation.title
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-gray-50">
        {messages.length === 0 ? (
          <div className="text-center py-8">
            <div className="text-gray-500">
              <Bot className="w-8 h-8 mx-auto mb-3 text-gray-300" />
              <p>Start the conversation by sending a message below.</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-3xl flex ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <div className={`flex-shrink-0 ${message.role === 'user' ? 'ml-3' : 'mr-3'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center shadow-sm ${
                    message.role === 'user' 
                      ? 'btn-primary text-white' 
                      : 'bg-white text-gray-600'
                  }`}>
                    {message.role === 'user' ? (
                      <User className="w-4 h-4" />
                    ) : (
                      <Bot className="w-4 h-4" />
                    )}
                  </div>
                </div>
                <div className={`rounded-lg px-4 py-3 shadow-sm ${
                  message.role === 'user' 
                    ? 'btn-primary text-white' 
                    : 'bg-white text-gray-900'
                }`}>
                  <p className="text-sm">{message.content}</p>
                  <p className={`text-xs mt-2 ${
                    message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}>
                    {formatTime(message.timestamp)}
                  </p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="px-6 py-4 bg-white shadow-sm">
        <div className="flex space-x-4">
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className="w-full px-4 py-3 bg-gray-50 rounded-lg focus:outline-none focus:ring-2  focus:bg-white resize-none transition-colors"
              rows={1}
              style={{ maxHeight: '120px', minHeight: '44px' }}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim()}
            className="px-4 py-3 btn-primary text-white rounded-lg  transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConversationInterface;