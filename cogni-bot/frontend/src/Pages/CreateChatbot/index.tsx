import React from 'react';
import { useNavigate } from 'react-router-dom';
import ChatbotCreator from '../../components/ChatbotCreator';
import { Chatbot } from '../../types';

const CreateChatbotPage: React.FC = () => {
  const navigate = useNavigate();

  const handleChatbotCreate = (chatbot: Chatbot) => {
    // Navigate back to chatbots page after successful creation
    // Add a small delay to ensure the toast message is shown
    setTimeout(() => {
      navigate('/');
    }, 1000);
  };

  const handleClose = () => {
    // Navigate back to chatbots page
    navigate('/');
  };

  const handlePromptReady = (chatbotId: string, prompt: string) => {
    // Handle prompt ready if needed
    console.log('Prompt ready for chatbot:', chatbotId);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChatbotCreator
        onChatbotCreate={handleChatbotCreate}
        onClose={handleClose}
        onPromptReady={handlePromptReady}
      />
    </div>
  );
};

export default CreateChatbotPage; 