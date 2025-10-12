// import React, { useState } from 'react';
// import { ChevronDown, Check } from 'lucide-react';
// import { useAppContext } from '../../context/AppContext';

// const ChatbotSelector: React.FC = () => {
//   const { chatbots, selectedChatbotId, setSelectedChatbotId } = useAppContext();
//   const [isOpen, setIsOpen] = useState(false);

//   const selectedChatbot = chatbots.find(p => p.id === selectedChatbotId);

//   return (
//     <div className="relative">
//       <button
//         onClick={() => setIsOpen(!isOpen)}
//         className="flex items-center justify-between w-full px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:focus:ring-offset-gray-900"
//       >
//         <span>{selectedChatbot?.name || 'Select a chatbot'}</span>
//         <ChevronDown size={16} className="ml-2" />
//       </button>
      
//       {isOpen && (
//         <div className="absolute left-0 z-10 mt-1 w-full bg-white dark:bg-gray-800 shadow-lg rounded-md py-1 scale-in origin-top">
//           {chatbots.map(chatbot => (
//             <button
//               key={chatbot.id}
//               onClick={() => {
//                 setSelectedChatbotId(chatbot.id);
//                 setIsOpen(false);
//               }}
//               className="flex items-center justify-between w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
//             >
//               <span>{chatbot.name}</span>
//               {chatbot.id === selectedChatbotId && (
//                 <Check size={16} className="text-blue-500" />
//               )}
//             </button>
//           ))}
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
