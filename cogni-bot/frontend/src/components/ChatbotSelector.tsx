// import React, { useState } from 'react';
// import { Chatbot } from '../types';
// import { ChevronDown, Database, Brain, Settings, Plus } from 'lucide-react';

// interface ChatbotSelectorProps {
//   chatbots: Chatbot[];
//   onChatbotSelect: (chatbot: Chatbot) => void;
//   onCreateChatbot: () => void;
//   selectedChatbot: Chatbot | null;
// }

// const ChatbotSelector: React.FC<ChatbotSelectorProps> = ({ 
//   chatbots, 
//   onChatbotSelect, 
//   onCreateChatbot,
//   selectedChatbot 
// }) => {
//   const [isOpen, setIsOpen] = useState(false);
//   const [showSettings, setShowSettings] = useState(false);
//   const [tempChatbot, setTempChatbot] = useState<Chatbot | null>(null);

//   const handleChatbotClick = (chatbot: Chatbot) => {
//     setTempChatbot(chatbot);
//     setShowSettings(true);
//     setIsOpen(false);
//   };

//   const handleConfirmSelection = () => {
//     if (tempChatbot) {
//       onChatbotSelect(tempChatbot);
//       setShowSettings(false);
//       setTempChatbot(null);
//     }
//   };

//   const getStatusColor = (status: string) => {
//     switch (status) {
//       case 'active': return 'bg-green-100 text-green-800';
//       case 'inactive': return 'bg-red-100 text-red-800';
//       case 'draft': return 'bg-yellow-100 text-yellow-800';
//       default: return 'bg-gray-100 text-gray-800';
//     }
//   };

//   if (chatbots.length === 0) {
//     return (
//       <div className="bg-gray-50 rounded-lg p-8 text-center">
//         <div className="mx-auto w-16 h-16 bg-white rounded-full flex items-center justify-center mb-4 shadow-sm">
//           <Plus className="w-8 h-8 text-gray-400" />
//         </div>
//         <h3 className="text-lg font-medium text-gray-900 mb-2">No Chatbots Available</h3>
//         <p className="text-gray-600 mb-4">Create your first chatbot to get started with conversation AI.</p>
//         <button
//           onClick={onCreateChatbot}
//           className="inline-flex items-center px-4 py-2 btn-primary text-white font-medium rounded-lg transition-colors shadow-sm"
//         >
//           <Plus className="w-4 h-4 mr-2" />
//           Create Chatbot
//         </button>
//       </div>
//     );
//   }

//   return (
//     <div className="relative">
//       <div className="bg-gray-50 rounded-lg shadow-sm">
//         <button
//           onClick={() => setIsOpen(!isOpen)}
//           className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-100 transition-colors rounded-lg"
//         >
         
//           <ChevronDown className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
//         </button>

//         {isOpen && (
//           <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg z-10">
//             <div className="py-2">
//               <button
//                 onClick={() => {
//                   onCreateChatbot();
//                   setIsOpen(false);
//                 }}
//                 className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors flex items-center"
//               >
//                 <Plus className="w-4 h-4 mr-3 text-blue-600" />
//                 <span className="text-blue-600 font-medium">Create New Chatbot</span>
//               </button>
//               <div className="h-px bg-gray-100 mx-2"></div>
//               {chatbots.map((chatbot) => (
//                 <button
//                   key={chatbot.chatbot_id}
//                   onClick={() => handleChatbotClick(chatbot)}
//                   className="w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors"
//                 >
//                   <div className="flex items-center justify-between">
//                     <div>
//                       <h3 className="font-medium text-gray-900">{chatbot.name}</h3>
//                     </div>
//                     <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(chatbot.status)}`}>
//                       {chatbot.status}
//                     </span>
//                   </div>
//                 </button>
//               ))}
//             </div>
//           </div>
//         )}
//       </div>

//       {showSettings && tempChatbot && (
//         <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
//           <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
//             <div className="px-6 py-4">
//               <h2 className="text-xl font-semibold text-gray-900 flex items-center">
//                 <Settings className="w-5 h-5 mr-2" />
//                 Configure Chatbot Settings
//               </h2>
//               <p className="text-gray-600 mt-1">{tempChatbot.name}</p>
//             </div>

//             <div className="px-6 py-4 space-y-6">
//               <div>
//                 <h3 className="text-lg font-medium text-gray-900 flex items-center mb-4">
//                   <Database className="w-5 h-5 mr-2" />
//                   Database Settings
//                 </h3>
//                 <div className="grid grid-cols-2 gap-4">
//                   <div>
//                     <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
//                     <input
//                       type="text"
//                       value={tempChatbot.type}
//                       readOnly
//                       className="w-full px-3 py-2 bg-gray-50 rounded-md"
//                     />
//                   </div>
//                   <div>
//                     <label className="block text-sm font-medium text-gray-700 mb-1">Host</label>
//                     <input
//                       type="text"
//                       value={tempChatbot.host}
//                       readOnly
//                       className="w-full px-3 py-2 bg-gray-50 rounded-md"
//                     />
//                   </div>
//                   <div>
//                     <label className="block text-sm font-medium text-gray-700 mb-1">Port</label>
//                     <input
//                       type="number"
//                       value={tempChatbot.port}
//                       readOnly
//                       className="w-full px-3 py-2 bg-gray-50 rounded-md"
//                     />
//                   </div>
//                   <div>
//                     <label className="block text-sm font-medium text-gray-700 mb-1">Database</label>
//                     <input
//                       type="text"
//                       value={tempChatbot.database}
//                       readOnly
//                       className="w-full px-3 py-2 bg-gray-50 rounded-md"
//                     />
//                   </div>
//                 </div>
//               </div>

//               <div>
//                 <h3 className="text-lg font-medium text-gray-900 flex items-center mb-4">
//                   <Brain className="w-5 h-5 mr-2" />
//                   AI Model Settings
//                 </h3>
//                 <div className="grid grid-cols-2 gap-4">
                
//                   <div>
//                     <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
//                     <input
//                       type="text"
//                       value={tempChatbot.model}
//                       readOnly
//                       className="w-full px-3 py-2 bg-gray-50 rounded-md"
//                     />
//                   </div>
                  
//                 </div>
//               </div>
//             </div>

//             <div className="px-6 py-4 bg-gray-50 flex justify-end space-x-4 rounded-b-lg">
//               <button
//                 onClick={() => setShowSettings(false)}
//                 className="px-4 py-2 text-gray-700 bg-white rounded-md hover:bg-gray-50 transition-colors shadow-sm"
//               >
//                 Cancel
//               </button>
//               <button
//                 onClick={handleConfirmSelection}
//                 className="px-4 py-2 btn-primary text-white rounded-md hover:bg-[#6658dd] transition-colors shadow-sm"
//               >
//                 Confirm Selection
//               </button>
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// };

// export default ChatbotSelector;
import React from 'react'

function ChatbotSelector() {
  return (
    <div>
      
    </div>
  )
}

export default ChatbotSelector
