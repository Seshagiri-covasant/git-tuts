import React, { useEffect, useState } from "react";
import {
  Plus,
  Trash2,
  MessageSquare,
  Search,
  Calendar,
  Brain,
  FileText,
  Database,
} from "lucide-react";
import { useAppContext } from "../../context/AppContext";
import ConversationModal from "../../Modals/ConversationModal";
import {
  deleteConversation,
  getAllConversations,
  getDBgetName,
  getChatbotDetails,
  getChatbotTemplate,
} from "../../services/api";
import { useParams } from "react-router-dom";
import { Conversation } from "../../types";
import ChatbotDelete from "../../Modals/ChatbotDelete";
import LLMEditor from "../LLMEditor";
import TemplateEditor from "../TemplateEditor";
import Loader from "../Loader";

const Sidebar: React.FC = () => {
  const {
    selectedChatbotId,
    selectedConversationId,
    setSelectedChatbotId,
    setConversations,
    setSelecedConversationName,
    setSelectedConversationId,
    isSidebarCollapsed,
  } = useAppContext();
  const [filteredConversations, setFilteredConversations] = useState<
    Conversation[]
  >([]);
  const [searchTerm, setSearchTerm] = useState('');
  const[isLoader,setLoader] = useState(false)
  const [openModal, setOpenModal] = useState(false);
  // const [expandedChatbots, setExpandedChatbots] = useState<Set<string>>();
  const { chatbotId } = useParams();
  const [chatbotData, setChatbotData] = useState<any>(null);
  const [showLLMEditor, setShowLLMEditor] = useState(false);
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState<any>(null);
  const [isDbUpdating, setIsDbUpdating] = useState(false);

  useEffect(() => {
    getAllConverstions();
    getChatbotDtls();
  }, [chatbotId]);

  useEffect(() => {
    if (filteredConversations.length > 0) {
      selectConv(filteredConversations[0]);
    }
  }, [filteredConversations]);

  const selectConv = (conversation: any) => {
    setSelectedConversationId(conversation.conversationId);
    setSelecedConversationName(conversation.conversationName);
  };

  const getChatbotDtls = async () => {
    try {
      const res = await getChatbotDetails(chatbotId);
      setChatbotData(res.data);
      setSelectedChatbotId(res.data.chatbot_id);
      
      // Fetch template details if template_id exists
      if (res.data.template_id) {
        try {
          const templateRes = await getChatbotTemplate(chatbotId);
          setCurrentTemplate(templateRes.data.template);
        } catch (error) {
          // Template might not exist, that's okay
        }
      }
    } catch (error) {
    } finally {
    }
  };

  const getAllConverstions = async () => {
    try {
      setLoader(true)
      const res = await getAllConversations(chatbotId);
      setFilteredConversations(res.data);
      setConversations(res.data);
      selectConv(res.data[0]); // Select the first conversation by default
      setSelectedConversationId(res.data[0]?.conversationId || null);
      setSelecedConversationName(res.data[0]?.conversationName || null);
    } catch (error) {
    } finally {
      setTimeout(() => {
        setLoader(false)
      }, 800);
    }
  };

  const closeModal = () => {
    setOpenModal(false);
    getAllConverstions();
  };

  const handleCreateConversation = () => {
    setOpenModal(true);
  };

  const [conv_Id, setConvId] = useState<string | null>(null);
  const [isShow, setShowModal] = useState<boolean>(false);
  
  const deleteConv = async (conversation: any) => {
    setConvId(conversation.conversationId);
    setShowModal(true);
  };

  const closeMoidal = () => {
    setShowModal(false);
  };

  const onDelete = async () => {
    try {
      setLoader(true)
      await deleteConversation(chatbotId, conv_Id);
      setSelectedConversationId(null); // Clear selected conversation after deletion
      getAllConverstions(); // Refresh conversations list
      closeMoidal();
    } catch (error) {
      console.error("Error deleting conversation:", error);
    }finally{
      setLoader(false)
    }
  };

  const searchedConversations = filteredConversations.filter((conv) =>
    conv.conversationName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const sortedConversations = searchedConversations.sort((a, b) => {
    // Pinned conversations always come first
    if (a.conversationType === 'PINNED' && b.conversationType !== 'PINNED') return -1;
    if (a.conversationType !== 'PINNED' && b.conversationType === 'PINNED') return 1;
    
    // If both are pinned or both are not pinned, sort by startTime (newest first)
    const timeA = new Date(a.startTime).getTime();
    const timeB = new Date(b.startTime).getTime();
    return timeB - timeA;
  });

  const handleLLMUpdate = async (newLLM: string, newTemperature?: number) => {
    // Completely refresh chatbot data from backend to ensure latest values
    try {
      const res = await getChatbotDetails(chatbotId);
      setChatbotData(res.data);
      
      // Update template if needed
      if (res.data.template_id) {
        try {
          const templateRes = await getChatbotTemplate(chatbotId);
          setCurrentTemplate(templateRes.data.template);
        } catch (error) {
          // Template might not exist, that's okay
        }
      }
    } catch (error) {
      console.error("Error refreshing chatbot data:", error);
      // Fallback to manual update if API fails
      setChatbotData((prev: any) => ({
        ...prev,
        current_llm_name: newLLM,
        temperature: newTemperature || prev.temperature
      }));
    }
  };

  const handleTemplateUpdate = (template: any) => {
    setCurrentTemplate(template);
    setChatbotData((prev: any) => ({
      ...prev,
      template_name: template.name
    }));
  };

  const handleDbUpdate = async () => {
    if (!chatbotId || isDbUpdating) return;
    
    try {
      setIsDbUpdating(true);
      
      // Future implementation will call the actual API endpoint
      // await updateDatabaseSchema(chatbotId);
      
      // For now, simulate the API call with a delay
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Refresh chatbot data to reflect any updates
      await getChatbotDtls();
      
      console.log('Database schema update completed for chatbot:', chatbotId);
      
      // TODO: Add success notification to user
      // showToast('Database schema updated successfully', 'success');
      
    } catch (error) {
      console.error('Database update failed:', error);
      // TODO: Add proper error handling and user notification
      // showToast('Failed to update database schema', 'error');
    } finally {
      setIsDbUpdating(false);
    }
  };

  return (
    <>
    <aside className={`h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ${
      isSidebarCollapsed ? "w-16" : "w-80"
    }`}>
      {isLoader && <Loader />}
      

      {!isSidebarCollapsed && (
        <div className="flex flex-col h-full">
          <div className="p-6 border-b dark:border-gray-700 bg-white dark:bg-gray-900 w-full max-w-sm">
            {/* Header */}
            <div className="flex justify-between items-start mb-2">
              <h2 className="text-base font-bold text-gray-800 dark:text-white">
                Chatbot:{" "}
                <span className="font-semibold text-[#6658dd] dark:text-blue-400">
                  {chatbotData?.chatbot_name}
                </span>
              </h2>
            </div>

            {/* Details Section */}
            <div className="space-y-3 text-sm text-gray-800 dark:text-gray-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="font-medium text-gray-600 dark:text-gray-400">Model Name:</span>
                  <span className="ml-2 text-xs font-semibold text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-full">
                    {getDBgetName(chatbotData?.current_llm_name)}
                  </span>
                </div>
                <button
                  onClick={() => setShowLLMEditor(true)}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  title="Edit LLM Settings"
                >
                  <Brain className="w-3 h-3" />
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="font-medium text-gray-600 dark:text-gray-400">Temperature:</span>
                  <span className="ml-2 text-xs font-semibold text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded-full">
                    {chatbotData?.temperature || 0.7}
                  </span>
                </div>
                {/* Key badge removed as requested */}
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="font-medium text-gray-600 dark:text-gray-400">Prompt Template:</span>
                  <span className="ml-2">{chatbotData?.template_name}</span>
                </div>
                <button
                  onClick={() => setShowTemplateEditor(true)}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
                  title="Edit Template"
                >
                  <FileText className="w-3 h-3" />
                </button>
              </div>
              
              <div className="flex flex-col space-y-2">
              <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-600 dark:text-gray-400 text-xs">Target DB:</span>
                <button
                  onClick={handleDbUpdate}
                  disabled={!selectedChatbotId || isDbUpdating || !chatbotData?.db_url}
                    className={`p-1.5 rounded-md transition-all duration-200 flex items-center space-x-1 flex-shrink-0 ${
                    selectedChatbotId && !isDbUpdating && chatbotData?.db_url
                      ? "text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:text-emerald-300 dark:hover:bg-emerald-900/30 shadow-sm hover:shadow-md border border-emerald-200 dark:border-emerald-800"
                      : "text-gray-300 dark:text-gray-600 cursor-not-allowed border border-gray-200 dark:border-gray-700"
                  } ${isDbUpdating ? "animate-pulse" : ""}`}
                  title={
                    selectedChatbotId && chatbotData?.db_url
                      ? isDbUpdating 
                        ? "Refreshing database schema..."
                        : "Sync database schema • Get latest table structures and fresh data"
                      : chatbotData?.db_url ? "Select a chatbot first" : "No database configured"
                  }
                >
                    <Database size={12} className={isDbUpdating ? "animate-spin" : ""} />
                  <span className="text-xs font-medium">
                    {isDbUpdating ? "Syncing..." : "Sync DB"}
                  </span>
                </button>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-2">
                  <span className="text-xs text-gray-600 dark:text-gray-300 break-all leading-relaxed">
                    {chatbotData?.db_url || 'No database configured'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Conversations Section */}
          <div className="flex-1 flex flex-col  overflow-y-auto">
            <div className="px-4 pt-3 flex justify-between items-center">
              <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wide">
                Conversations
              </h2>
              <button
                onClick={handleCreateConversation}
                disabled={!selectedChatbotId}
                className={`p-1.5 rounded-md transition-colors ${
                  selectedChatbotId
                    ? "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                    : "text-gray-300 dark:text-gray-600 cursor-not-allowed"
                }`}
                title={
                  selectedChatbotId
                    ? "New conversation"
                    : "Select a chatbot first"
                }
              >
                <Plus size={16} />
              </button>
            </div>
            <div className="relative px-4 pt-3 border-b border-gray-200 dark:border-gray-800 pb-3">
              <Search className="absolute left-8 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search conversations..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-colors"
              />
            </div>
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              <div className="p-2 space-y-1 mt-2">
                {selectedChatbotId || chatbotId ? (
                  (() => {
                    // const chatbotConversations = getChatbotConversations(selectedChatbotId);
                    return sortedConversations.length > 0 ? (
                      sortedConversations.map((conversation) => (
                        <div
                          key={conversation.conversationId}
                          className={`group rounded-lg transition-all ${
                            selectedConversationId ===
                            conversation.conversationId
                              ? "bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800"
                              : "hover:bg-gray-50 dark:hover:bg-gray-800/50"
                          } ${
                            conversation.conversationType === 'PINNED'
                              ? "border-l-4 border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20"
                              : ""
                          }`}
                        >
                          <div
                            onClick={() => selectConv(conversation)}
                            className="w-full text-left px-3 py-3 text-sm cursor-pointer"
                          >
                            <div className="flex items-center space-x-3">
                              <div
                                className={`p-1.5 rounded-md mt-0.5 ${
                                  selectedConversationId ===
                                  conversation.conversationId
                                    ? "bg-blue-100 dark:bg-blue-800 text-[#6658dd] dark:text-blue-400"
                                    : "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400"
                                }`}
                              >
                                <MessageSquare size={14} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center space-x-2">
                                  <h4
                                    className={`font-bold truncate ${
                                      selectedConversationId ===
                                      conversation.conversationId
                                        ? "text-[#6658dd] dark:text-blue-300"
                                        : conversation.conversationType === 'PINNED'
                                        ? "text-yellow-700 dark:text-yellow-300"
                                        : "text-gray-700 dark:text-gray-300"
                                    }`}
                                  >
                                    {conversation.conversationName}
                                  </h4>
                                  {conversation.conversationType === 'PINNED' && (
                                    <svg 
                                      className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" 
                                      fill="currentColor" 
                                      viewBox="0 0 20 20"
                                    >
                                      <title>Pinned conversation</title>
                                      <path d="M5 4a2 2 0 012-2h6a2 2 0 012 2v14l-5-2.5L5 18V4z" />
                                    </svg>
                                  )}
                                </div>
                                <div className={`flex items-center space-x-1 mt-1 text-xs ${
                                  selectedConversationId === conversation.conversationId
                                    ? 'text-[#6658dd] dark:text-blue-400'
                                    : conversation.conversationType === 'PINNED'
                                    ? 'text-yellow-600 dark:text-yellow-400'
                                    : 'text-gray-500 dark:text-gray-400'
                                }`}>
                                  <Calendar size={10} />
                                  <span>{new Date(conversation.startTime).toLocaleDateString()}</span>
                                  {conversation.owner && (
                                    <>
                                      <span>•</span>
                                      <span>{conversation.owner}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                              <div className="group-hover:opacity-100 transition-opacity flex">
                                <button
                                  className="text-gray-400 hover:text-red-600 dark:hover:text-red-400 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700"
                                  onClick={() => deleteConv(conversation)}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8">
                        <MessageSquare
                          size={32}
                          className="mx-auto text-gray-300 dark:text-gray-600 mb-2"
                        />
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          No conversations yet
                        </p>
                        <button
                          onClick={handleCreateConversation}
                          className="mt-2 text-sm text-[#6658dd]"
                        >
                          Start your first conversation
                        </button>
                      </div>
                    );
                  })()
                ) : (
                  <div className="text-center py-8">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Select a chatbot to view conversations
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {openModal && <ConversationModal onClose={closeModal} />}
      {isShow && (
        <ChatbotDelete
          title="Delete Conversation"
          name="Are you sure you want to delete this conversation? This action cannot be undone."
          chatbotId={conv_Id || ""}
          onClose={closeMoidal}
          onDelete={onDelete}
        />
      )}
      {showLLMEditor && (
        <LLMEditor
          chatbotId={chatbotData?.chatbot_id}
          currentLLM={chatbotData?.current_llm_name}
          currentTemperature={chatbotData?.temperature}
          onClose={() => setShowLLMEditor(false)}
          onUpdate={handleLLMUpdate}
        />
      )}
      {showTemplateEditor && (
        <TemplateEditor
          chatbotId={chatbotData?.chatbot_id}
          currentTemplate={currentTemplate}
          onClose={() => setShowTemplateEditor(false)}
          onUpdate={handleTemplateUpdate}
        />
      )}
    </aside>
    </>
  );
};

export default Sidebar;