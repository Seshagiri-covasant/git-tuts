import React, { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom';
import EmptyState from '../../components/EmptyState'
import ChatbotTable from '../../components/ChatbotTable'
import { getChatbots } from '../../services/api';
import { Chatbot } from '../../types';
import { dummyChatbots } from '../../data/dummyData';
import Loader from '../../components/Loader';

function Chatbots() {
  const[isLoader,setLoader] = useState(false)
  const navigate = useNavigate();
  const location = useLocation();
  const [chatbots, setChatbots] = useState<Chatbot[]>(dummyChatbots);
    useEffect(() => {
      getAllChatbots()
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Refresh data when user returns to this page or when logo is clicked
    useEffect(() => {
      const handleFocus = () => {
        getAllChatbots();
      };

      window.addEventListener('focus', handleFocus);
      return () => window.removeEventListener('focus', handleFocus);
    }, []);

    // Listen for location state changes (when logo is clicked)
    useEffect(() => {
      if (location.state?.refresh) {
        getAllChatbots();
      }
    }, [location.state]);
  const getAllChatbots = async () => {
    try {
      setLoader(true)
     const response = await getChatbots();
     setChatbots(response.data);
    } catch (error) {
    }finally {
      setTimeout(() => {
        setLoader(false)
      },800)
    }
   
  };  
   const [selectedChatbots, setSelectedChatbot] = useState<Chatbot | null>(null);
  const handleChatbotCreate = (chatbot: Chatbot) => {
        setChatbots(prev => [chatbot, ...prev]);
        setSelectedChatbot(chatbot);
      };

  return (
 <>
 {
  isLoader && <Loader />
 }
  <div className="flex-1 overflow-hidden">
    {chatbots.length === 0 ? (
      <div className="bg-white rounded-lg shadow-sm p-8">
        <EmptyState type="chatbots" onAction={() => navigate('/create-chatbot')} />
      </div>
    ) : (
      <div className="h-full px-6 py-4  pb-10">
      
        <div className="h-full overflow-y-auto rounded-lg bg-white shadow-sm p-4">
          <ChatbotTable
            onRefresh={getAllChatbots}
            chatbots={chatbots}
          />
        </div>
      </div>
    )}

  </div>
  </>

  )
}

export default Chatbots
