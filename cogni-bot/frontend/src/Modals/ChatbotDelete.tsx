import React, { useState } from 'react';
import { Chatbot } from '../types';
import { X, Database, Brain, Plus, Check } from 'lucide-react';
import { configureChatbotDatabase, createConversation, createChatbot, createTemplate, deleteChatbot, setLLMSettings } from '../services/api';
import { useParams } from 'react-router-dom';
import { useToaster } from '../Toaster/Toaster';

interface ChatbotCreatorProps {
  onClose: () => void;
  onDelete: () => void;
  chatbotId: string;
  name:string;
  title:string;
}

const ChatbotDelete: React.FC<ChatbotCreatorProps> = ({title, onClose,chatbotId,name,onDelete }) => {
 

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-screen overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-3 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-lg modalHead">{title}</h2>
              
          </div>
         
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

    <div className="px-6 py-3">
            <p className="text-gray-600 text-sm mt-1">
              {name}
            </p>
            </div>

       

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          <button 
          onClick={onClose}
            className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >Cancel
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-2 btn-primary text-white rounded-md transition-colors flex items-center"
          >
          Yes, Delete
          </button>
        </div>
      </div>
    </div>
  );
};



export default ChatbotDelete
