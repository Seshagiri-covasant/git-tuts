// import React, { useState } from 'react';
// import { Plus, X, Folder, Calendar } from 'lucide-react';
// import { useAppContext } from '../../context/AppContext';

// const ChatbotManager: React.FC = () => {
//   const { chatbots, createChatbot, selectedChatbotId, setSelectedChatbotId } = useAppContext();
//   const [showCreateForm, setShowCreateForm] = useState(false);
//   const [formData, setFormData] = useState({
//     name: '',
//     description: ''
//   });

//   const handleSubmit = (e: React.FormEvent) => {
//     e.preventDefault();
//     if (formData.name.trim()) {
//       createChatbot(formData.name.trim(), formData.description.trim());
//       setFormData({ name: '', description: '' });
//       setShowCreateForm(false);
//     }
//   };

//   const handleCancel = () => {
//     setFormData({ name: '', description: '' });
//     setShowCreateForm(false);
//   };

//   return (
//     <div className="h-full overflow-y-auto bg-white dark:bg-gray-900 p-4">
//       <div className="flex items-center justify-between mb-4">
//         <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">Chatbot Manager</h2>
//       </div>

//       {/* Create Chatbot Button */}
//       {!showCreateForm && (
//         <button
//           onClick={() => setShowCreateForm(true)}
//           className="w-full mb-4 p-3 border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg text-gray-500 dark:text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors flex items-center justify-center space-x-2"
//         >
//           <Plus size={20} />
//           <span>Create New Chatbot</span>
//         </button>
//       )}

//       {/* Create Chatbot Form */}
//       {showCreateForm && (
//         <div className="mb-4 p-4 border border-gray-200 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800">
//           <form onSubmit={handleSubmit} className="space-y-3">
//             <div>
//               <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
//                 Chatbot Name *
//               </label>
//               <input
//                 type="text"
//                 value={formData.name}
//                 onChange={(e) => setFormData({ ...formData, name: e.target.value })}
//                 placeholder="Enter chatbot name"
//                 className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
//                 required
//               />
//             </div>
//             <div>
//               <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
//                 Description
//               </label>
//               <textarea
//                 value={formData.description}
//                 onChange={(e) => setFormData({ ...formData, description: e.target.value })}
//                 placeholder="Enter chatbot description"
//                 rows={3}
//                 className="w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
//               />
//             </div>
//             <div className="flex space-x-2">
//               <button
//                 type="submit"
//                 className="flex-1 bg-[#6658dd] text-white py-2 px-4 rounded-md transition-colors"
//               >
//                 Create Chatbot
//               </button>
//               <button
//                 type="button"
//                 onClick={handleCancel}
//                 className="flex-1 bg-gray-300 dark:bg-gray-600 hover:bg-gray-400 dark:hover:bg-gray-500 text-gray-700 dark:text-gray-300 py-2 px-4 rounded-md transition-colors"
//               >
//                 Cancel
//               </button>
//             </div>
//           </form>
//         </div>
//       )}

//       {/* Chatbots Table */}
//       {chatbots.length > 0 ? (
//         <div className="space-y-2">
//           <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
//             Chatbots ({chatbots.length})
//           </h3>
//           <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
//             {chatbots.map(chatbot => (
//               <div
//                 key={chatbot.id}
//                 onClick={() => setSelectedChatbotId(chatbot.id)}
//                 className={`p-3 rounded-lg border cursor-pointer transition-all ${
//                   selectedChatbotId === chatbot.id
//                     ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 shadow-sm'
//                     : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50'
//                 }`}
//               >
//                 <div className="flex items-start space-x-3">
//                   <div className={`p-2 rounded-md ${
//                     selectedChatbotId === chatbot.id
//                       ? 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-400'
//                       : 'bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400'
//                   }`}>
//                     <Folder size={16} />
//                   </div>
//                   <div className="flex-1 min-w-0">
//                     <h4 className={`font-medium truncate ${
//                       selectedChatbotId === chatbot.id
//                         ? 'text-blue-900 dark:text-blue-100'
//                         : 'text-gray-900 dark:text-gray-100'
//                     }`}>
//                       {chatbot.name}
//                     </h4>
//                     {chatbot.description && (
//                       <p className={`text-sm mt-1 line-clamp-2 ${
//                         selectedChatbotId === chatbot.id
//                           ? 'text-blue-700 dark:text-blue-300'
//                           : 'text-gray-600 dark:text-gray-400'
//                       }`}>
//                         {chatbot.description}
//                       </p>
//                     )}
//                     <div className={`flex items-center space-x-1 mt-2 text-xs ${
//                       selectedChatbotId === chatbot.id
//                         ? 'text-blue-600 dark:text-blue-400'
//                         : 'text-gray-500 dark:text-gray-400'
//                     }`}>
//                       <Calendar size={12} />
//                       <span>{new Date(chatbot.createdAt).toLocaleDateString()}</span>
//                     </div>
//                   </div>
//                 </div>
//               </div>
//             ))}
//           </div>
//         </div>
//       ) : (
//         <div className="text-center py-8">
//           <Folder size={48} className="mx-auto text-gray-300 dark:text-gray-600 mb-3" />
//           <p className="text-gray-500 dark:text-gray-400">No chatbots yet</p>
//           <p className="text-sm text-gray-400 dark:text-gray-500">Create your first chatbot to get started</p>
//         </div>
//       )}
//     </div>
//   );
// };

// export default ChatbotManager;
import React from 'react'

function ChatbotManager() {
  return (
    <div>
      
    </div>
  )
}

export default ChatbotManager
