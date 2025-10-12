import React from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";
import { useAppContext } from "../../context/AppContext";
import LLMSettings from "../features/LLMSettings";
import DBSettings from "../features/DBSettings";
import ChatInterface from "../features/ChatInterface";
import TestSuiteInterface from "../features/TestSuiteInterface";
import CustomTestSuiteInterface from "../features/CustomTestSuiteInterface";
import { Route, Routes, useLocation } from "react-router-dom";
import Chatbots from "../../Pages/Chatbots";
import Templates from "../../Pages/Templates";
import PackagingPage from "../../Pages/Packaging";
import StandaloneChatbot from "../../Pages/Standalone";
import CreateChatbotPage from "../../Pages/CreateChatbot";
// EDIT SCHEMA FEATURE: Import the new EditSchema page component
import EditSchema from "../../Pages/EditSchema";


const Layout: React.FC = () => {
  const { isSidebarCollapsed, activeSettingsTab, selectedConversationId, conversations } =
    useAppContext();
  const location = useLocation();

  // Check if current conversation is Test Suite or Custom Test Suite
  const currentConversation = conversations.find(
    (conv) => conv.conversationId === selectedConversationId
  );
  const isTestSuite = currentConversation?.conversationName === 'Test Suite';
  const isCustomTestSuite = currentConversation?.conversationName === 'Custom Test Suite';

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900">
      {/* Only show Header if not on Standalone or Edit Schema routes */}
      { !location.pathname.startsWith('/standalone/') && !location.pathname.includes('/edit-schema') && (
        <div className="fixed top-0 left-0 right-0 z-20">
          <Header />
        </div>
      )}
      <Routes>
        <Route path="/" element={
          <div className="pt-[70px]">
            <Chatbots />
          </div>
        } />
        <Route path="/chatbots" element={
          <div className="pt-[70px]">
            <Chatbots />
          </div>
        } />
        <Route path="/templates" element={
          <div className="pt-[70px]">
            <Templates />
          </div>
        } />
        <Route path="/create-chatbot" element={<CreateChatbotPage />} />
        <Route path="/chatbot/:chatbotId/package" element={<PackagingPage />} />
        {/* EDIT SCHEMA FEATURE: New route for editing semantic schemas */}
        <Route path="/chatbot/:chatbotId/edit-schema" element={<EditSchema />} />
        <Route path="/standalone/:chatbotId" element={<StandaloneChatbot />} />
        
        <Route
          path="/chatbot/:chatbotId"
          element={
            <div className="flex h-screen pt-[70px]"> {/* Full height with top padding for fixed header */}
              <Sidebar />

              <main className="flex-1 overflow-hidden flex flex-col">
                <div className="flex flex-1 min-h-0">
                  {/* Chat Area */}
                  <div className="flex-1 overflow-hidden p-4">
                    {selectedConversationId ? (
                      isTestSuite ? (
                        <TestSuiteInterface />
                      ) : isCustomTestSuite ? (
                        <CustomTestSuiteInterface />
                      ) : (
                        <ChatInterface />
                      )
                    ) : (
                      <div className="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
                        <div className="text-center">
                          <h2 className="text-xl font-medium mb-2">
                            No conversation selected
                          </h2>
                          <p>Select a conversation from the sidebar or create a new one</p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </main>
            </div>
          }
        />
      </Routes>
    </div>
  );
};

export default Layout;
