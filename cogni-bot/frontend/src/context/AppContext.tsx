import React, { createContext, useContext, useState } from 'react';
import { Chatbot, Conversation, LLMSettings, DBSettings, Message } from '../types';
import { 
  SAMPLE_PROJECTS, 
  SAMPLE_CONVERSATIONS, 
  DEFAULT_LLM_SETTINGS, 
  DEFAULT_DB_SETTINGS 
} from '../utils/constants';

interface AppContextProps {
  chatbots: Chatbot[];
  selectedChatbotId: string | null;
  conversations: Conversation[];
  selectedConversationId: string | null;
  llmSettings: LLMSettings;
  dbSettings: DBSettings;
  isSidebarCollapsed: boolean;
  activeSettingsTab: string | null;
  isVoiceEnabled: boolean;
  isSpeaking: boolean;
  selectedConversationName:string | null;
  benchmarkingChatbotId: string | null;
  setSelecedConversationName: React.Dispatch<React.SetStateAction<string | null>>;
  setSelectedChatbotId: (id: string | null) => void;
  setSelectedConversationId: (id: string | null) => void;
  updateLLMSettings: (settings: Partial<LLMSettings>) => void;
  updateDBSettings: (settings: Partial<DBSettings>) => void;
  toggleSidebar: () => void;
  setActiveSettingsTab: (tab: string | null) => void;
  createNewConversation: () => void;
  addMessageToConversation: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  toggleVoice: () => void;
  setIsSpeaking: (isSpeaking: boolean) => void;
  setBenchmarkingChatbotId: (id: string | null) => void;

  // Proper types:
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>;
  // setConversationsData: () => void; // <-- Define this if you're using it, or remove
}

const AppContext = createContext<AppContextProps | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [chatbots, setChatbots] = useState<Chatbot[]>(SAMPLE_PROJECTS);
  const [selectedChatbotId, setSelectedChatbotId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>(SAMPLE_CONVERSATIONS);
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    SAMPLE_CONVERSATIONS.find(c => c.chatbotId === selectedChatbotId)?.id || null
  );
  const [selectedConversationName, setSelecedConversationName] = useState<string | null>(null);
  const [benchmarkingChatbotId, setBenchmarkingChatbotId] = useState<string | null>(null);
  const [llmSettings, setLLMSettings] = useState<LLMSettings>(DEFAULT_LLM_SETTINGS);
  const [dbSettings, setDBSettings] = useState<DBSettings>(DEFAULT_DB_SETTINGS);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<string | null>(null);
  const [isVoiceEnabled, setIsVoiceEnabled] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  const updateLLMSettings = (settings: Partial<LLMSettings>) => {
    setLLMSettings(prev => ({ ...prev, ...settings }));
  };

  const updateDBSettings = (settings: Partial<DBSettings>) => {
    setDBSettings(prev => ({ ...prev, ...settings }));
  };

  const createNewConversation = () => {
    if (!selectedChatbotId) return;
    
    const newId = `new-${Date.now()}`;
    // const newConversation: Conversation = {
    //   id: newId,
    //   chatbotId: selectedChatbotId,
    //   title: 'New Conversation',
    //   createdAt: new Date().toISOString(),
    //   updatedAt: new Date().toISOString(),
    //   messages: [],
    // };
    
    setConversations(prev => [ ...prev]);
    setSelectedConversationId(newId);
  };

  const addMessageToConversation = (message: Omit<Message, 'id' | 'timestamp'>) => {
    if (!selectedConversationId) return;
    
    const newMessage: Message = {
      ...message,
      id: `msg-${Date.now()}`,
      timestamp: new Date().toISOString(),
    };
    
    setConversations(prev => 
      prev.map(conv => 
        conv.id === selectedConversationId 
          ? { 
              ...conv, 
              messages: [...conv.messages, newMessage],
              updatedAt: new Date().toISOString(),
              title: message.role === 'user' && conv.messages.length === 0 
                ? message.content.slice(0, 30) + (message.content.length > 30 ? '...' : '') 
                : conv.title
            } 
          : conv
      )
    );
    
    // Simulate AI response after user message
    if (message.role === 'user') {
      setTimeout(() => {
        const aiResponse: Message = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          content: `This is a simulated response to: "${message.content}"`,
          timestamp: new Date().toISOString(),
        };
        
        setConversations(prev => 
          prev.map(conv => 
            conv.id === selectedConversationId 
              ? { 
                  ...conv, 
                  messages: [...conv.messages, aiResponse],
                  updatedAt: new Date().toISOString(),
                } 
              : conv
          )
        );
      }, 1500);
    }
  };

  const toggleVoice = () => {
    setIsVoiceEnabled(!isVoiceEnabled);
  };

  return (
    <AppContext.Provider value={{
      chatbots,
      selectedChatbotId,
      conversations,
      selectedConversationId,
      llmSettings,
      dbSettings,
      isSidebarCollapsed,
      activeSettingsTab,
      isVoiceEnabled,
      isSpeaking,
      selectedConversationName,
      setSelecedConversationName,
      benchmarkingChatbotId,
      setBenchmarkingChatbotId,

      setSelectedChatbotId,
      setSelectedConversationId,
      updateLLMSettings,
      updateDBSettings,
      toggleSidebar,
      setActiveSettingsTab,
      createNewConversation,
      setConversations,
      addMessageToConversation,
      toggleVoice,
      setIsSpeaking,
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};