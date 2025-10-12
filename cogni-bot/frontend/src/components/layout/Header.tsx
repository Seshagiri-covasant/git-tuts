import React, { useState } from 'react';
import { Menu, MessageSquare, Folder, FileText, Settings } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import logoSm from "../../assets/images/logo-sm.png";
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import GlobalAISettingsModal from '../../Modals/GlobalAISettingsModal';

const Header: React.FC = () => {
  const { 
    toggleSidebar
  } = useAppContext();
const { chatbotId } = useParams();
const [showSettingsModal, setShowSettingsModal] = useState(false);

const navigate=useNavigate()
const chatbotNav=()=>{
  // Force navigation by adding a timestamp to force re-render
  if (location.pathname === '/' || location.pathname === '/chatbots') {
    navigate('/', { replace: true, state: { refresh: Date.now() } });
  } else {
    navigate('/');
  }
}
const location = useLocation();

  // Only show sidebar toggle on conversation pages
  const showSidebarToggle = location.pathname.startsWith('/chatbot/');

  return (
    <header className="h-[70px] bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4 shadow-sm z-10">
      <div className="flex items-center">
         {showSidebarToggle && (
           <button 
            onClick={toggleSidebar}
            className="p-2 rounded-md cursor-pointer text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Menu size={20} />
          </button>
         )}
        <div className="cursor-pointer ml-4 flex items-center space-x-4" onClick={() => {
          // Force navigation by adding a timestamp to force re-render
          if (location.pathname === '/') {
            navigate('/', { replace: true, state: { refresh: Date.now() } });
          } else {
            navigate('/');
          }
        }}> 
          {/* Company Logo - Using the provided "C" logo image */}
          <img 
            src={logoSm} 
            alt="Covasant Logo" 
            className="w-12 h-12 object-contain"
          />
          
          {/* Product Name */}
          <div className="flex flex-col">
            <span 
              className="text-2xl font-bold text-gray-900 dark:text-gray-100"
              style={{ letterSpacing: '-0.5px' }}
            > 
              Cognibot
            </span>
            <span 
              className="text-base font-medium text-gray-600 dark:text-gray-400"
              style={{ letterSpacing: '0.5px' }}
            > 
              Studio
            </span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center space-x-2">
        <button
                onClick={ 
                  chatbotNav}
                className={`flex items-center px-3 py-1.5 rounded-lg transition-colors  ${
                  location.pathname === '/' || location.pathname === '/chatbots'
                    ? 'btn-primary'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Folder className="w-4 h-4 mr-2" />
                Chatbots
              </button>
              <button
                onClick={() => {
                  // Force navigation by adding a timestamp to force re-render
                  if (location.pathname === '/templates') {
                    navigate('/templates', { replace: true, state: { refresh: Date.now() } });
                  } else {
                    navigate('/templates');
                  }
                }}
                className={`flex items-center px-3 py-1.5 rounded-lg transition-colors ${
                  location.pathname === '/templates'
                    ? 'btn-primary'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <FileText className="w-4 h-4 mr-2" />
                Templates
              </button>
              <button
                onClick={() => {
                  if (chatbotId) {
                    // Force navigation by adding a timestamp to force re-render
                    if (location.pathname === `/chatbot/${chatbotId}`) {
                      navigate(`/chatbot/${chatbotId}`, { replace: true, state: { refresh: Date.now() } });
                    } else {
                      navigate(`/chatbot/${chatbotId}`);
                    }
                  }
                }}
                disabled={!chatbotId}
                className={`flex items-center px-4 py-2 rounded-lg transition-colors ${
                  location.pathname.includes('/chatbot/') 
                    ? 'btn-primary'
                    : chatbotId
                    ? 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    : 'text-gray-400 cursor-not-allowed'
                }`}
              >
                <MessageSquare className="w-4 h-4 mr-2" />
                Conversations
              </button>
              <button
                onClick={() => setShowSettingsModal(true)}
                className="p-2 rounded-md transition-colors text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                title="Settings"
              >
                <Settings size={20} />
              </button>
        {/* <button 
          onClick={toggleVoice}
          className={`p-2 rounded-md transition-colors ${
            isVoiceEnabled 
              ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30' 
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
          title={isVoiceEnabled ? "Disable voice" : "Enable voice"}
        >
          {isVoiceEnabled ? (
            <Mic size={20} className={isSpeaking ? "animate-pulse" : ""} />
          ) : (
            <MicOff size={20} />
          )}
        </button>
        
        <button 
          onClick={() => setActiveSettingsTab(activeSettingsTab === 'llm' ? null : 'llm')}
          className={`p-2 rounded-md transition-colors ${
            activeSettingsTab === 'llm' 
              ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30' 
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
          title="LLM Settings"
        >
          <MessageSquare size={20} />
        </button>
        
        <button 
          onClick={() => setActiveSettingsTab(activeSettingsTab === 'db' ? null : 'db')}
          className={`p-2 rounded-md transition-colors ${
            activeSettingsTab === 'db' 
              ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30' 
              : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
          title="Database Settings"
        >
          <Settings size={20} />
        </button> */}
      </div>
      
      {/* Global AI Settings Modal */}
      {showSettingsModal && (
        <GlobalAISettingsModal onClose={() => setShowSettingsModal(false)} />
      )}
    </header>
  );
};

export default Header;