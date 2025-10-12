import React, { useState, useEffect } from 'react';
import { Conversation, Chatbot } from '../types';
import { Search, Plus, MessageCircle, Calendar, Hash, ChevronLeft, ChevronRight, Menu } from 'lucide-react';
import { createConversation, getAllConversations, deleteConversation } from '../services/api';
import ConversationModal from '../Modals/ConversationModal';
import { useParams } from 'react-router-dom';

interface ConversationSidebarProps {
  conversations: Conversation[];
  selectedConversation: Conversation | null;
  selectedChatbot: Chatbot | null;
  onConversationSelect: (conversation: Conversation) => void;
  onNewConversation: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  selectedConversation,
  selectedChatbot,
  onConversationSelect,
  onNewConversation,
  collapsed,
  onToggleCollapse
}) => {
  const { chatbotId } = useParams();
  const [openModal, setOpenModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredConversations, setFilteredConversations] = useState<Conversation[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const conversationsPerPage = 10;
const onCreateConv=()=>{
onNewConversation()
}
useEffect(() => {
   getAllConverstions()
  }
, []);

  // Listen for createNewConversation event from ChatInterface
  useEffect(() => {
    const handleCreateNewConversation = () => {
      setOpenModal(true);
    };

    window.addEventListener('createNewConversation', handleCreateNewConversation);
    
    return () => {
      window.removeEventListener('createNewConversation', handleCreateNewConversation);
    };
  }, []);

const closeModal = () => {
  setOpenModal(false);
  // Refresh conversations list after modal closes
  getAllConverstions();
};

const getAllConverstions=async ()=>{
  try{
    const res= await getAllConversations(chatbotId);
    setFilteredConversations(res.data);
  }catch(error){
  }finally {
  }
}

  const paginatedConversations = filteredConversations.slice(
    (currentPage - 1) * conversationsPerPage,
    currentPage * conversationsPerPage
  );

  // Sort conversations: pinned first, then by startTime (newest first)
  const sortedConversations = filteredConversations.sort((a, b) => {
    // Pinned conversations always come first
    if (a.conversationType === 'PINNED' && b.conversationType !== 'PINNED') return -1;
    if (a.conversationType !== 'PINNED' && b.conversationType === 'PINNED') return 1;
    
    // If both are pinned or both are not pinned, sort by startTime (newest first)
    const timeA = new Date(a.startTime).getTime();
    const timeB = new Date(b.startTime).getTime();
    return timeB - timeA;
  });

  const paginatedSortedConversations = sortedConversations.slice(
    (currentPage - 1) * conversationsPerPage,
    currentPage * conversationsPerPage
  );

  const totalPages = Math.ceil(sortedConversations.length / conversationsPerPage);
  
  // Remove the direct conversation creation function and use modal instead
  const openNewConversationModal = () => {
    setOpenModal(true);
  };

  const onDelete = async (conversationId: string) => {
    try {
      const response = await deleteConversation(chatbotId, conversationId);
      closeModal();
    } catch {
      // Handle error
    } finally {
      // Handle cleanup
    }
  };
  if (collapsed) {
    return (
      <div className="h-full flex flex-col">
        {/* Collapsed Header */}
        <div className="p-4 border-b border-gray-100">
          <button
            onClick={onToggleCollapse}
            className="w-full p-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center justify-center"
            title="Expand Sidebar"
          >
            <ChevronRight className="w-4 h-4 text-gray-600" />
          </button>
        </div>

        {/* Collapsed New Conversation Button */}
        <div className="p-4">
          <button
          onClick={openNewConversationModal}
            className="w-full p-2 btn-primary text-white rounded-lg  transition-colors flex items-center justify-center"
            title="New Conversation"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Collapsed Conversations */}
        <div className="flex-1 overflow-y-auto px-2">
          {sortedConversations.slice(0, 5).map((conversation) => (
            <button
              key={conversation.conversationId || conversation.id}
              onClick={() => onConversationSelect(conversation)}
              className={`w-full p-2 rounded-lg mb-2 transition-all relative ${
                selectedConversation?.id === (conversation.conversationId || conversation.id)
                  ? 'btn-primary ring-1 '
                  : 'hover:bg-gray-100'
              } ${
                conversation.conversationType === 'PINNED' 
                  ? 'border-l-2 border-yellow-400 bg-yellow-50' 
                  : ''
              }`}
              title={`${conversation.conversationName}${conversation.conversationType === 'PINNED' ? ' (Pinned)' : ''}`}
            >
              <MessageCircle className="w-4 h-4 text-gray-600 mx-auto" />
              {conversation.conversationType === 'PINNED' && (
                <div className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-500 rounded-full"></div>
              )}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-100">
         {selectedChatbot && (
          <div className="mb-6 p-4 btn-primary rounded-lg border border-blue-100">
            <div className="flex items-center text-sm ">
              <MessageCircle className="w-4 h-4 mr-2" />
              <span className="font-medium">{selectedChatbot.name}</span>
            </div>
          </div>
        )}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
          <div className="flex items-center space-x-2">
            <button
             onClick={openNewConversationModal}
              className="p-2 btn-primary text-white rounded-lg  transition-colors shadow-sm"
              title="New Conversation"
            >
              <Plus className="w-4 h-4" />
            </button>
            <button
              onClick={onToggleCollapse}
              className="p-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
              title="Collapse Sidebar"
            >
              <ChevronLeft className="w-4 h-4 text-gray-600" />
            </button>
          </div>
        </div>

       

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="text-center py-8 text-gray-500 px-4">
            <MessageCircle className="w-8 h-8 mx-auto mb-3 text-gray-300" />
            <p className="text-sm">
              {searchTerm ? 'No conversations found' : 'No conversations yet'}
            </p>
            <p className="text-xs mt-1">
              {searchTerm ? 'Try different keywords' : 'Start a new conversation to get started'}
            </p>
          </div>
        ) : (
          <div className="px-4 py-2 mt-2">
            {paginatedSortedConversations.map((conversation, index) => {
              // Use conversationId if available, otherwise fall back to id
              const conversationId = conversation.conversationId || conversation.id;
              
              return (
                <div key={conversationId}>
                  <div
                    onClick={() => onConversationSelect(conversation)}
                    className={`w-full p-3 rounded-lg text-left transition-all mb-2 ${
                      selectedConversation?.id === conversationId
                        ? 'bg-blue-50 shadow-md ring-1 ring-blue-200 border-blue-200'
                        : 'hover:bg-gray-50 hover:shadow-sm border-gray-100 bg-white'
                    } ${
                      conversation.conversationType === 'PINNED' 
                        ? 'border-l-4 border-yellow-400 bg-yellow-50' 
                        : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center">
                          {/* Pin icon for pinned conversations */}
                          {conversation.conversationType === 'PINNED' && (
                            <svg 
                              className="w-3.5 h-3.5 text-yellow-500 mr-1.5 flex-shrink-0 mt-0.5" 
                              fill="currentColor" 
                              viewBox="0 0 20 20"
                            >
                              <title>Pinned conversation</title>
                              <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                            </svg>
                          )}
                          <h3 className={`font-medium text-sm line-clamp-1 ${
                            conversation.conversationType === 'PINNED' 
                              ? 'text-yellow-700' 
                              : 'text-gray-900'
                          }`}>
                            {conversation.conversationName || 'Untitled Conversation'}
                          </h3>
                        </div>
                        
                        <div className="flex items-center mt-1">
                          <p className="text-xs text-gray-500 truncate">
                            {conversation.owner || 'Unknown'}
                          </p>
                          <span className="mx-1 text-gray-300">•</span>
                          <p className="text-xs text-gray-400">
                            {conversation.startTime ? new Date(conversation.startTime).toLocaleDateString() : ''}
                          </p>
                        </div>
                      </div>
                      
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDelete(conversationId);
                        }}
                        className="text-gray-400 hover:text-red-500 p-1 -mr-2"
                        title="Delete conversation"
                      >
                        <svg 
                          className="w-4 h-4" 
                          fill="none" 
                          stroke="currentColor" 
                          viewBox="0 0 24 24"
                        >
                          <path 
                            strokeLinecap="round" 
                            strokeLinejoin="round" 
                            strokeWidth={2} 
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" 
                          />
                        </svg>
                      </button>
                    </div>
                  </div>
                  {/* Separator line between conversations */}
                  {index < paginatedSortedConversations.length - 1 && (
                    <div className="h-px bg-gray-100 mx-2 mb-3"></div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="p-4 border-t border-gray-100 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <div className="flex space-x-2">
              <button
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                Previous
              </button>
              <button
                onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 bg-white border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}
      {
        openModal &&
        <ConversationModal 
          onClose={closeModal}
          onConversationCreated={(conversation) => {
            // Map the conversation data to match the frontend interface
            const mappedConversation = {
              ...conversation,
              id: conversation.conversationId, // Ensure id field is set
              title: conversation.conversationName, // Map conversationName to title
              createdAt: conversation.startTime, // Map startTime to createdAt
              updatedAt: conversation.startTime, // Map startTime to updatedAt
              messages: [], // Initialize empty messages array
              chatbotId: chatbotId // Add chatbotId
            };
            // Select the newly created conversation
            onConversationSelect(mappedConversation);
          }}
        />
      }
    </div>
  );
};

export default ConversationSidebar;