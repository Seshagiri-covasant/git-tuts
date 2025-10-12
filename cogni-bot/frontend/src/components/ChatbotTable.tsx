import React, { useState } from 'react';
import { Chatbot } from '../types';
import { Database, Brain, Calendar, Activity, Plus, X, Trash2, Search } from 'lucide-react';
import {
  Card,
  Row,
  Col,
  Badge,
  Button,
  Form,
  InputGroup,
  Table,
  Pagination,
  Modal,
} from "react-bootstrap";

import { activateForReady, deleteChatbot, getDBgetName, getStatusName, startBenchmark } from '../services/api';
import { useNavigate } from 'react-router-dom';

import { dummyChatbots } from '../data/dummyData';
import { useToaster } from '../Toaster/Toaster';
import ChatbotDelete from '../Modals/ChatbotDelete';
import Loader from './Loader';
import { useAppContext } from '../context/AppContext';
import { useContext } from 'react';

interface ChatbotTableProps {
  chatbots: Chatbot[];
  onRefresh: () => void;
}

const ChatbotTable: React.FC<ChatbotTableProps> = ({ chatbots, onRefresh }) => {
  const [isLoader, setLoader] = useState(false);

  const navigate = useNavigate();
  const { showToast } = useToaster();
  const { setBenchmarkingChatbotId } = useAppContext();
  const [chatbot, setChatbots] = useState<Chatbot[]>(dummyChatbots);
  const [selectedChatbots, setSelectedChatbot] = useState<Chatbot | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [chatbot_id, setChatbot] = useState<string | null>(null);
  const [isShow, setShowModal] = useState<boolean>(false);
  const [showActivationModal, setShowActivationModal] = useState(false);
  const [activatingChatbotId, setActivatingChatbotId] = useState<string | null>(null);
  const [includeSchemaDetails, setIncludeSchemaDetails] = useState(true);
  const [finalPromptContent, setFinalPromptContent] = useState<string>("");
  const [chatbotPrompts, setChatbotPrompts] = useState<{ [id: string]: string }>({});

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800';
      case 'inactive': return 'bg-red-100 text-red-800';
      case 'draft': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const extractDatabaseName = (dbUrl: string) => {
    if (!dbUrl) return 'NA';
    try {
      // Extract database name and type from URL
      // Format: postgresql+psycopg2://user:password@host:port/database_name
      const match = dbUrl.match(/\/\/(?:[^\/]+@)?[^\/]+\/([^?]+)/);
      if (match) {
        const dbName = match[1];
        // Determine database type from URL
        let dbType = 'Unknown';
        if (dbUrl.includes('postgresql')) {
          dbType = 'PostgreSQL';
        } else if (dbUrl.includes('mysql')) {
          dbType = 'MySQL';
        } else if (dbUrl.includes('sqlite')) {
          dbType = 'SQLite';
        } else if (dbUrl.includes('bigquery')) {
          dbType = 'BigQuery';
        }
        return `${dbName} (${dbType})`;
      }
      return dbUrl;
    } catch (error) {
      return dbUrl;
    }
  };

  const handleChatbotCreate = (chatbot: Chatbot) => {
    setChatbots(prev => [chatbot, ...prev]);
    setSelectedChatbot(chatbot);
  };

  const close = () => {
    setShowModal(false);
    onRefresh();
  };

  const closeModal = () => {
    setShowModal(false);
    setChatbot(null);
  };

  const onDelete = async () => {
    try {
      setLoader(true);
      const res = await deleteChatbot(chatbot_id);
      onRefresh();
      showToast('Chatbot deleted successfully', 'success');
      closeModal();
    } catch (error: any) {
      showToast(error?.error, 'error');
      console.error("Error deleting chatbot:", error);
    } finally {
      setTimeout(() => {
        setLoader(false);
      }, 500);
    }
  };

  const startConversation = (chatbot: Chatbot) => {
    navigate(`/chatbot/${chatbot.chatbot_id}`);
  };

  const activateForConversation = async (chatbotId: string) => {
    try {
      setLoader(true);
      const readyRes = await activateForReady(chatbotId);
      if (readyRes.status === 200) {
        showToast('Chatbot activated and prompt sent to LLM, starting benchmark...', 'success');
        
        // Small delay to ensure database transaction is committed before benchmark
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Find the chatbot to get its temperature
        const chatbot = chatbots.find(c => c.chatbot_id === chatbotId);
        const temperature = chatbot?.temperature ?? 0.7;
        
        const benchmarkRes = await startBenchmark(chatbotId, temperature);
        if (benchmarkRes.status === 202) {
          setBenchmarkingChatbotId(chatbotId);
          showToast('Benchmark started successfully!', 'success');
        }
        onRefresh();
      }
    } catch (error) {
      showToast('An error occurred during activation.', 'error');
    } finally {
      setLoader(false);
    }
  };

  const handleActivateClick = (chatbotId: string) => {
    setActivatingChatbotId(chatbotId);
    setShowActivationModal(true);
    setIncludeSchemaDetails(true);
  };

  const handleActivateConfirm = () => {
    if (activatingChatbotId) {
      activateForConversation(activatingChatbotId);
      setShowActivationModal(false);
      setActivatingChatbotId(null);
    }
  };

  const handleActivateCancel = () => {
    setShowActivationModal(false);
    setActivatingChatbotId(null);
    setIncludeSchemaDetails(true);
  };

  const handleChatbotDelete = (chatbotId: string) => {
    setChatbot(chatbotId);
    setShowModal(true);
  };

  const filtered = chatbots.filter(chatbot =>
    [chatbot.name, chatbot.db_url, chatbot.status, chatbot.llm_name, chatbot.template_name]
      .some(field => field?.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div>
      {isLoader && <Loader />}

      <h2 className='mb-3'><b>Chatbots</b></h2>
      <Row className="mb-3 mt-2">
        <Col md={4}>
          <InputGroup>
            <InputGroup.Text>
              <Search className="w-4 h-4" />
            </InputGroup.Text>
            <Form.Control
              placeholder="Search Chatbots..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </InputGroup>
        </Col>
        <Col md={5}></Col>
        <Col md={3}>
          <div className='flex justify-end mb-2 bg-none'>
            <button
              onClick={() => navigate('/create-chatbot')}
              className="flex items-center px-4 py-2 btn-primary rounded-lg  transition-colors shadow-sm"
            >
              <Plus className="w-4 h-4 mr-2" />
              New Chatbot
            </button>
          </div>
        </Col>
      </Row>

      <div className="overflow-x-auto">
        <Table striped hover className="w-full min-w-max">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Chatbot
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Database
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                AI Model
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Prompt Template
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {(filtered).map((chatbot) => (
              <tr key={chatbot.chatbot_id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{chatbot.name}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div>
                      <div 
                        className="text-sm font-medium text-gray-900 cursor-help" 
                        title={chatbot.db_url || 'No database configured'}
                      >
                        {extractDatabaseName(chatbot.db_url)}
                      </div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div>
                      <div className="text-sm text-gray-500">{getDBgetName(chatbot.llm_name)}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm text-gray-900">{formatDate(chatbot.created_at)}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm text-gray-900">{chatbot.template_name || 'Default'}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(chatbot.status)}`}>
                    <Activity className="w-3 h-3 mr-1" />
                    {getStatusName(chatbot.status)}
                  </span>
                </td>
                <td className=" border-b border-gray-300 text-sm text-gray-500 bg-white font-normal cursor-pointer whitespace-nowrap pt-3">
                  <div className="flex items-center">
                    {chatbot.status === 'template_configured' && (
                      <Button
                        variant="primary"
                        className="  flex items-center px-4 py-2 btn-priamry rounded-lg transition-colors"
                        onClick={() => handleActivateClick(chatbot.chatbot_id)}
                      >Activate For Conversations
                      </Button>)}
                    {chatbot.status === 'ready' && (
                      <>
                        <Button
                          variant="primary"
                          className="btn-primary flex items-center px-4 py-2 rounded-lg transition-colors mr-2"
                          onClick={() => startConversation(chatbot)}
                        >Start Conversation
                        </Button>
                        <Button
                          variant="success"
                          className="bg-green-600 hover:bg-green-700 text-white flex items-center px-4 py-2 rounded-lg transition-colors mr-2"
                          onClick={() => navigate(`/chatbot/${chatbot.chatbot_id}/package`)}
                        >Package & Deploy
                        </Button>
                      </>
                    )}
                    {/* EDIT SCHEMA FEATURE: Edit Schema Button in Chatbot Table */}
                    {/* 
                      This button allows users to edit the semantic schema (ER diagram) 
                      for existing chatbots directly from the main chatbots list.
                      Only shown for chatbots that have a database configured (db_url exists).
                    */}
                    {chatbot.db_url && (
                      <Button
                        variant="outline-primary"
                        className="border-blue-600 text-blue-600 hover:bg-blue-50 flex items-center px-3 py-2 rounded-lg transition-colors mr-2"
                        onClick={() => navigate(`/chatbot/${chatbot.chatbot_id}/edit-schema`)}
                      >
                        <Database className="w-4 h-4 mr-1" />
                        Edit Schema
                      </Button>
                    )}
                    <div
                      title="Delete"
                      onClick={() => handleChatbotDelete(chatbot.chatbot_id)}
                    >
                      <Trash2
                        className="w-6 h-6 ml-4 text-gray-500 hover:text-gray-700 cursor-pointer"
                      />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>

      {isShow && (
        <ChatbotDelete title="Delete Chatbot" name="Are you sure you want to delete this chatbot? This action cannot be undone."
          chatbotId={chatbot_id || ''}
          onClose={closeModal}
          onDelete={onDelete}
        />
      )}
      {showActivationModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">
                Activate Chatbot
              </h2>
              <button
                onClick={handleActivateCancel}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 py-4">
              <p className="text-gray-700 mb-4">
                Configure activation settings for your chatbot. Your template provides instructions, and sample data is always included for context.
              </p>
              
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <input
                    type="checkbox"
                    id="includeSchemaDetails"
                    checked={includeSchemaDetails}
                    onChange={(e) => setIncludeSchemaDetails(e.target.checked)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <div className="flex-1">
                    <label htmlFor="includeSchemaDetails" className="text-sm font-medium text-gray-900">
                      Include Detailed Schema Information
                    </label>
                    <p className="text-sm text-gray-600 mt-1">
                      Includes detailed database schema structure (table relationships, column types, constraints) along with sample data for enhanced SQL generation.
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 p-3 bg-blue-50 rounded-md border border-blue-200">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> Sample data from your tables is always included for context. 
                  The detailed schema option adds table structure, column types, and relationships for even better SQL accuracy.
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                onClick={handleActivateCancel}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleActivateConfirm}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
              >
                Activate Chatbot
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatbotTable;