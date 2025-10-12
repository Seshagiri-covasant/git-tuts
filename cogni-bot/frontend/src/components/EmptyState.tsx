import React from 'react';
import { Plus, Folder, MessageSquare } from 'lucide-react';

interface EmptyStateProps {
  type: 'chatbots' | 'conversations';
  onAction: () => void;
}

const EmptyState: React.FC<EmptyStateProps> = ({ type, onAction }) => {
  if (type === 'chatbots') {
    return (
      <div className="text-center py-12">
        <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
          <Folder className="w-12 h-12 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Chatbots Yet</h3>
        <p className="text-gray-600 mb-6 max-w-md mx-auto text-base">
          Get started by creating your first conversation AI chatbot. Configure your database and AI model settings to begin.
        </p>
        <button
          onClick={onAction}
          className="inline-flex items-center px-6 py-3 btn-primary font-medium rounded-lg  transition-colors"
        >
          <Plus className="w-5 h-5 mr-2" />
          Create Your First Chatbot
        </button>
      </div>
    );
  }

  return (
    <div className="text-center py-12">
      <div className="mx-auto w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
        <MessageSquare className="w-12 h-12 text-gray-400" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">No Conversations Yet</h3>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        Start your first conversation with the AI assistant. Create meaningful interactions and build your conversation history.
      </p>
      <button
        onClick={onAction}
        className="inline-flex items-center px-6 py-3  font-medium rounded-lg btm-primary transition-colors"
      >
        <Plus className="w-5 h-5 mr-2" />
        Start New Conversation
      </button>
    </div>
  );
};

export default EmptyState;