import React, { useState } from 'react';
import { Chatbot } from '../types';
import { X, Database, Brain, Plus, Check, MessageSquare, BarChart3 } from 'lucide-react';
import { configureChatbotDatabase, createConversation, createChatbot, createTemplate, setLLMSettings } from '../services/api';
import { useParams } from 'react-router-dom';
import Loader from '../components/Loader';

interface ChatbotCreatorProps {
  onClose: () => void;
  onConversationCreated?: (conversation: any) => void;
}

const ConversationModal: React.FC<ChatbotCreatorProps> = ({ onClose, onConversationCreated }) => {
  const [formData, setFormData] = useState({
    name: '',
    owner: ''
  });
  const [loader, setLoader] = useState(false);
  const { chatbotId } = useParams();
  const [isTemp, setTemplate] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [templates, setTemplates] = useState<any[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');

  // Predefined conversation types - removed "Test Suite" option
  const conversationTypes = [
    {
      name: 'New Conversation',
      description: 'Start a regular chat conversation',
      icon: MessageSquare,
      value: 'New Conversation'
    },
    {
      name: 'Custom Test Suite',
      description: 'Create and run your own SQL tests',
      icon: BarChart3,
      value: 'Custom Test Suite'
    }
  ];

  const [selectedType, setSelectedType] = useState(conversationTypes[0]);

  const validateStep = (step: number) => {
    const newErrors: Record<string, string> = {};
    if (step === 1) {
      if (!formData.name.trim()) newErrors.name = 'Conversation name is required';
      if (!formData.owner.trim()) newErrors.owner = 'Owner name is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    setLoader(true);
    if (validateStep(1)) {
      try {
        const chatbotResponse = await createConversation(chatbotId, formData.name, formData.owner);
        
        // Call the callback with the created conversation data
        if (onConversationCreated && chatbotResponse.data?.conversation) {
          onConversationCreated(chatbotResponse.data.conversation);
        }
      } catch (error: any) {
        console.error('Error creating conversation:', error);
      } finally {
        setLoader(false);
      }

      onClose();
    } else {
      setLoader(false);
    }
  };

  const updateFormData = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };
 
  const handleTypeSelect = (type: any) => {
    setSelectedType(type);
    // Set default name based on type
    if (type.value === 'New Conversation') {
      updateFormData('name', 'New Conversation');
    } else if (type.value === 'Custom Test Suite') {
      updateFormData('name', 'Custom Test Suite');
    }
  };

  return (
    <>
      {loader && <Loader/>}
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-screen overflow-y-auto">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold modalHead">Create New Conversation</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Form Content */}
          <div className="px-6 py-4">
            <div className="space-y-4">
              {/* Conversation Type Selection */}
              <div>
                <label className="block text-sm font-medium mb-3">
                  Conversation Type *
                </label>
                <div className="space-y-2">
                  {conversationTypes.map((type) => {
                    const IconComponent = type.icon;
                    return (
                      <div
                        key={type.value}
                        onClick={() => handleTypeSelect(type)}
                        className={`p-3 border rounded-lg cursor-pointer transition-all ${
                          selectedType.value === type.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className={`p-2 rounded-md ${
                            selectedType.value === type.value
                              ? 'bg-blue-100 text-blue-600'
                              : 'bg-gray-100 text-gray-500'
                          }`}>
                            <IconComponent size={16} />
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{type.name}</h4>
                            <p className="text-sm text-gray-500">{type.description}</p>
                          </div>
                          {selectedType.value === type.value && (
                            <Check className="w-5 h-5 text-blue-600" />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Conversation Name Input - Only show for New Conversation */}
              {selectedType.value === 'New Conversation' && (
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Conversation Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => updateFormData('name', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                      errors.name ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder="Enter conversation name"
                  />
                  {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">
                  Owner Name *
                </label>
                <input
                  type="text"
                  value={formData.owner}
                  onChange={(e) => updateFormData('owner', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 ${
                    errors.owner ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter conversation owner"
                />
                {errors.owner && <p className="text-red-500 text-sm mt-1">{errors.owner}</p>}
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
            <button 
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              className="px-4 py-2 btn-primary text-white rounded-md transition-colors flex items-center"
            >
              Create Conversation
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ConversationModal
