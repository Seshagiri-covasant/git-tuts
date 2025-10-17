import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Send, Download, Mic, MicOff, BarChart3, Lightbulb, ChevronLeft, ChevronRight } from 'lucide-react';
import { getChatbotDetails, createInteraction, createConversation, getBAInsights, getVisualization } from '../../services/api';
import { exportToCSV } from '../../utils/csvUtils';
import { Chart } from 'react-chartjs-2';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: any[];
  sql?: string;
}

interface ChatbotDetails {
  chatbot_id: string;
  chatbot_name: string;
  db_type: string;
  current_llm_name: string;
  temperature: number;
  template_name: string;
}

// Voice recognition interface
interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
}

interface SpeechRecognitionEvent {
  results: SpeechRecognitionResult[][];
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start(): void;
  stop(): void;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: any) => void;
  onend: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

const colorPalettes = {
  blue: {
    primary: '#3B82F6',
    secondary: '#1E40AF', 
    accent: '#60A5FA',
    background: '#F8FAFC',
    text: '#1F2937'
  },
  green: {
    primary: '#10B981',
    secondary: '#047857',
    accent: '#34D399', 
    background: '#F0FDF4',
    text: '#1F2937'
  },
  purple: {
    primary: '#8B5CF6',
    secondary: '#5B21B6',
    accent: '#A78BFA',
    background: '#FAF5FF',
    text: '#1F2937'
  },
  orange: {
    primary: '#F97316',
    secondary: '#C2410C',
    accent: '#FB923C',
    background: '#FFF7ED',
    text: '#1F2937'
  },
  teal: {
    primary: '#14B8A6',
    secondary: '#0F766E',
    accent: '#5EEAD4',
    background: '#F0FDFA',
    text: '#1F2937'
  }
};

const StandaloneChatbot: React.FC = () => {
  const { chatbotId } = useParams<{ chatbotId: string }>();
  const [searchParams] = useSearchParams();
  const paletteId = searchParams.get('palette') || 'blue';
  const palette = colorPalettes[paletteId as keyof typeof colorPalettes] || colorPalettes.blue;
  
  console.log('StandaloneChatbot component loaded with chatbotId:', chatbotId);
  console.log('Current URL params:', { chatbotId, paletteId });

  const [chatbot, setChatbot] = useState<ChatbotDetails | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingChatbot, setIsLoadingChatbot] = useState(true);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);
  const [currentPage, setCurrentPage] = useState<{[key: string]: number}>({});
  const [isLoadingInsights, setIsLoadingInsights] = useState<{[key: string]: boolean}>({});
  const [insights, setInsights] = useState<{[key: string]: string}>({});
  const [visualizations, setVisualizations] = useState<{[key: string]: any}>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const ROWS_PER_PAGE = 10;

  useEffect(() => {
    console.log('useEffect triggered with chatbotId:', chatbotId);
    if (chatbotId && chatbotId !== 'undefined' && chatbotId !== 'null') {
      console.log('Initializing app with chatbotId:', chatbotId);
      initializeApp();
      initializeVoiceRecognition();
    } else {
      console.log('chatbotId not available, skipping initialization');
    }
  }, [chatbotId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Apply dynamic styles
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--primary-color', palette.primary);
    root.style.setProperty('--secondary-color', palette.secondary);
    root.style.setProperty('--accent-color', palette.accent);
    root.style.setProperty('--background-color', palette.background);
    root.style.setProperty('--text-color', palette.text);
  }, [palette]);

  const initializeVoiceRecognition = () => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInputValue(transcript);
        setIsListening(false);
      };

      recognition.onerror = (event: any) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      setRecognition(recognition);
    }
  };

  const toggleVoiceInput = () => {
    if (!recognition) {
      alert('Voice recognition is not supported in your browser.');
      return;
    }

    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      recognition.start();
      setIsListening(true);
    }
  };

  const initializeApp = async () => {
    try {
      setIsLoadingChatbot(true);
      
      // First load chatbot details
      console.log('Loading chatbot details...');
      const chatbotResponse = await getChatbotDetails(chatbotId!);
      const chatbotData = chatbotResponse.data;
      setChatbot(chatbotData);
      console.log('Chatbot loaded:', chatbotData);
      
      // Then create conversation
      console.log('Creating conversation...');
      const conversationResponse = await createConversation(chatbotId!);
      console.log('Full conversation response:', conversationResponse.data);
      const convId = conversationResponse.data.conversation?.conversationId;
      setConversationId(convId);
      console.log('Conversation created:', convId);
      
      // Finally add welcome message with chatbot name
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        type: 'assistant',
        content: `Hello! I'm ${chatbotData.chatbot_name || 'your AI assistant'}. I can help you query your data using natural language. Just ask me anything!`,
        timestamp: new Date()
      };
      setMessages([welcomeMessage]);
      console.log('Welcome message added');
      
    } catch (error) {
      console.error('Error initializing app:', error);
      // Show error message to user
      const errorMessage: ChatMessage = {
        id: 'error',
        type: 'assistant',
        content: 'Sorry, there was an error connecting to the chatbot. Please refresh the page and try again.',
        timestamp: new Date()
      };
      setMessages([errorMessage]);
    } finally {
      setIsLoadingChatbot(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    console.log('Send button clicked');
    console.log('Input value:', inputValue);
    console.log('Is loading:', isLoading);
    console.log('Conversation ID:', conversationId);
    console.log('Chatbot:', chatbot);

    if (!inputValue.trim()) {
      console.log('No input text, returning');
      return;
    }
    
    if (isLoading) {
      console.log('Already loading, returning');
      return;
    }
    
    if (!conversationId) {
      console.log('No conversation ID, returning');
      alert('Conversation not initialized. Please refresh the page.');
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    console.log('Adding user message:', userMessage);
    setMessages(prev => [...prev, userMessage]);
    const messageText = inputValue;
    setInputValue('');
    setIsLoading(true);

    try {
      console.log('Sending request to createInteraction:', conversationId, messageText);
      // Use the persistent conversation ID to go through the full agent pipeline
      const response = await createInteraction(conversationId, messageText);
      console.log('Received response:', response);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: response.final_result || response.response || 'I received your message.',
        timestamp: new Date(),
        data: response.raw_result_set,
        sql: response.cleaned_query,
        debug: response.debug
      };

      console.log('Adding assistant message:', assistantMessage);
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error in createInteraction:', error);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: `Sorry, I encountered an error while processing your request: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      console.log('Request completed');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleDownloadCSV = (data: any[], query: string) => {
    if (data && data.length > 0) {
      exportToCSV(data, `query_results_${Date.now()}.csv`);
    }
  };

  const handleBAInsights = async (messageId: string, data: any[], content: string) => {
    console.log('handleBAInsights called with chatbotId:', chatbotId);
    console.log('Type of chatbotId:', typeof chatbotId);
    console.log('chatbotId value:', chatbotId);
    console.log('URL pathname:', window.location.pathname);
    
    if (!chatbotId || chatbotId === 'undefined' || chatbotId === 'null') {
      console.error('Chatbot ID not available for BA insights');
      alert('Chatbot ID not available');
      return;
    }
    
    try {
      setIsLoadingInsights(prev => ({ ...prev, [messageId]: true }));
      console.log('Calling getBAInsights with:', { data: data.length, content, chatbotId });
      const response = await getBAInsights(data, content, chatbotId);
      setInsights(prev => ({ ...prev, [messageId]: response.data.summary }));
    } catch (error) {
      console.error('Error getting BA insights:', error);
      alert('Failed to get BA insights. Please try again.');
    } finally {
      setIsLoadingInsights(prev => ({ ...prev, [messageId]: false }));
    }
  };

  const handleVisualization = async (messageId: string, data: any[], sql: string) => {
    console.log('handleVisualization called with chatbotId:', chatbotId);
    console.log('Type of chatbotId:', typeof chatbotId);
    console.log('chatbotId value:', chatbotId);
    console.log('URL pathname:', window.location.pathname);
    
    if (!chatbotId || chatbotId === 'undefined' || chatbotId === 'null') {
      console.error('Chatbot ID not available for visualization');
      alert('Chatbot ID not available');
      return;
    }
    
    try {
      setIsLoadingInsights(prev => ({ ...prev, [messageId]: true }));
      console.log('Calling getVisualization with:', { data: data.length, sql, chatbotId });
      const response = await getVisualization(data, '', sql, chatbotId);
      setVisualizations(prev => ({ ...prev, [messageId]: response.data.chart_config }));
    } catch (error) {
      console.error('Error getting visualization:', error);
      alert('Failed to generate visualization. Please try again.');
    } finally {
      setIsLoadingInsights(prev => ({ ...prev, [messageId]: false }));
    }
  };

  // Safely render a value in table cell
  const renderCellValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "-";
    }
    if (typeof value === 'object') {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  const renderDataTable = (data: any[], messageId: string) => {
    if (!Array.isArray(data) || data.length === 0) return null;

    try {
      const columns = Object.keys(data[0] || {});
      if (columns.length === 0) return null;

      const page = currentPage[messageId] || 0;
      const startIndex = page * ROWS_PER_PAGE;
      const endIndex = startIndex + ROWS_PER_PAGE;
      const paginatedData = data.slice(startIndex, endIndex);
      const totalPages = Math.ceil(data.length / ROWS_PER_PAGE);

      return (
        <div className="mt-2 bg-white rounded-md border shadow-sm overflow-hidden">
          <div className="max-h-80 overflow-auto">
            <table className="min-w-full divide-y divide-gray-200" style={{ fontSize: '0.91rem' }}>
              <thead style={{ backgroundColor: palette.background }} className="sticky top-0">
                <tr>
                  {columns.map((column) => (
                    <th
                      key={column}
                      className="px-2 py-1 text-left text-[11px] font-semibold uppercase tracking-wider"
                      style={{ color: palette.text, fontWeight: 600 }}
                    >
                      {String(column)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {paginatedData.map((row, index) => (
                  <tr key={startIndex + index} className="hover:bg-gray-50">
                    {columns.map((column) => (
                      <td key={column} className="px-2 py-1 text-[12px] text-gray-900 whitespace-nowrap">
                        {renderCellValue(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        {/* Pagination and Info */}
        <div className="px-2 py-1 bg-gray-50 border-t flex items-center justify-between" style={{ fontSize: '0.85em' }}>
          <div className="text-xs text-gray-600">
            Fetched {startIndex + 1}-{Math.min(endIndex, data.length)} of {data.length} results
          </div>
          
          {totalPages > 1 && (
            <div className="flex items-center space-x-1">
              <button
                onClick={() => setCurrentPage(prev => ({ ...prev, [messageId]: Math.max(0, page - 1) }))}
                disabled={page === 0}
                className="p-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ color: palette.primary }}
              >
                <ChevronLeft size={14} />
              </button>
              <span className="text-xs text-gray-600">
                Page {page + 1} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => ({ ...prev, [messageId]: Math.min(totalPages - 1, page + 1) }))}
                disabled={page === totalPages - 1}
                className="p-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ color: palette.primary }}
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    );
    } catch (error) {
      console.error('Error rendering data table:', error);
      return <div className="mt-2 p-4 text-red-500">Error displaying table data</div>;
    }
  };

  const renderMessage = (message: ChatMessage) => {
    if (message.type === 'user') {
      return (
        <div className="flex justify-end">
          <div className="max-w-4xl">
            <div
              className="p-2 rounded-md shadow-sm text-white"
              style={{ backgroundColor: palette.primary, fontSize: '0.92rem', borderRadius: 8 }}
            >
              <div className="text-xs font-medium mb-0.5">You</div>
              <div className="whitespace-pre-wrap" style={{ fontSize: '0.95em' }}>{message.content}</div>
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5 text-right">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        </div>
      );
    }

    // Assistant message - show table only if data exists, otherwise show content
    if (message.data && message.data.length > 0) {
      return (
        <div className="flex justify-start">
          <div className="max-w-full w-full">
            {/* Just the table - no assistant name or content */}
            {renderDataTable(message.data, message.id)}
            
            {/* Action buttons */}
            <div className="flex gap-2 mt-3">
              <button
                onClick={() => handleDownloadCSV(message.data!, message.content)}
                className="flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors"
                style={{ 
                  backgroundColor: palette.accent, 
                  color: palette.secondary 
                }}
              >
                <Download size={14} /> Download CSV
              </button>

              {chatbotId && (
                <button
                  onClick={() => handleBAInsights(message.id, message.data!, message.content)}
                  disabled={isLoadingInsights[message.id]}
                  className="flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors bg-blue-100 text-blue-700 hover:bg-blue-200 disabled:opacity-50"
                >
                  <Lightbulb size={14} />
                  {isLoadingInsights[message.id] ? 'Loading...' : 'BA Insights'}
                </button>
              )}

              {chatbotId && (
                <button
                  onClick={() => handleVisualization(message.id, message.data!, message.sql || '')}
                  disabled={isLoadingInsights[message.id]}
                  className="flex items-center gap-1 px-3 py-1 rounded text-xs font-medium transition-colors bg-green-100 text-green-700 hover:bg-green-200 disabled:opacity-50"
                >
                  <BarChart3 size={14} />
                  {isLoadingInsights[message.id] ? 'Loading...' : 'Visualize'}
                </button>
              )}
            </div>

            {/* Show BA insights if available */}
            {insights[message.id] && (
              <div className="mt-3 p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                <div className="text-sm font-semibold text-blue-800 mb-1">Business Analysis Insights:</div>
                <div className="text-sm text-blue-700 whitespace-pre-wrap">{insights[message.id]}</div>
              </div>
            )}

            {/* Show visualization if available */}
            {visualizations[message.id] && (
              <div className="mt-3 p-3 bg-green-50 rounded-lg border-l-4 border-green-400">
                <div className="text-sm font-semibold text-green-800 mb-1">Visualization:</div>
                <div className="w-full max-w-2xl">
                  <Chart {...visualizations[message.id]} />
                </div>
              </div>
            )}

            <div className="text-[10px] text-gray-500 mt-0.5">
              {message.timestamp.toLocaleTimeString()}
            </div>
          </div>
        </div>
      );
    }

    // Regular assistant message without data
    return (
      <div className="flex justify-start">
        <div className="max-w-4xl">
          <div className="p-2 rounded-md shadow-sm bg-white border" style={{ fontSize: '0.92rem', borderRadius: 8 }}>
            <div className="text-xs font-medium mb-0.5">
              {chatbot?.chatbot_name || 'AI Assistant'}
            </div>
            <div className="whitespace-pre-wrap" style={{ fontSize: '0.95em' }}>{message.content}</div>
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };

  if (!chatbotId) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ backgroundColor: palette.background }}>
        <div className="text-center">
          <div className="text-red-500 text-xl mb-4">❌</div>
          <p style={{ color: palette.text }}>Chatbot ID not found in URL</p>
          <p style={{ color: palette.text }}>Current URL: {window.location.pathname}</p>
          <p style={{ color: palette.text }}>Expected format: /standalone/[chatbot-id]</p>
        </div>
      </div>
    );
  }

  if (isLoadingChatbot) {
    return (
      <div className="h-screen flex items-center justify-center" style={{ backgroundColor: palette.background }}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 mx-auto mb-4" style={{ borderColor: palette.primary }}></div>
          <p style={{ color: palette.text }}>Loading chatbot...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col" style={{ backgroundColor: palette.background }}>
      {/* Static Chatbot Name Header */}
      <header style={{ background: palette.primary, color: '#fff', padding: '10px 0', fontSize: '1.1rem', fontWeight: 600, textAlign: 'center', letterSpacing: '0.02em', boxShadow: '0 2px 8px rgba(0,0,0,0.03)' }}>
        {chatbot?.chatbot_name || 'Chatbot'}
      </header>
      {/* Chat Area - maximize height, reduce padding */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-2" style={{ fontSize: '0.93rem' }}>
          {messages.map((message) => (
            <div key={message.id}>
              {renderMessage(message)}
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border rounded-lg p-2 shadow-sm" style={{ fontSize: '0.93rem' }}>
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2" style={{ borderColor: palette.primary }}></div>
                  <span className="text-sm text-gray-600">
                    {chatbot?.chatbot_name || 'AI'} is processing with {chatbot?.current_llm_name} (temp: {chatbot?.temperature})...
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        {/* Input Area - reduce padding, font size, and height */}
        <div className="border-t bg-white px-2 py-2" style={{ borderColor: palette.accent }}>
          <div className="flex space-x-2 items-end">
            <div className="flex-1">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your data..."
                className="w-full px-3 py-2 border rounded-lg resize-none focus:outline-none focus:ring-2"
                style={{ borderColor: palette.accent, fontSize: '0.95rem', minHeight: 32, maxHeight: 60, '--tw-ring-color': palette.primary } as React.CSSProperties}
                rows={1}
                disabled={isLoading}
              />
            </div>
            {/* Voice Input Button */}
            <button
              onClick={toggleVoiceInput}
              disabled={isLoading}
              className={`px-3 py-2 rounded-lg font-medium transition-colors ${
                isListening
                  ? 'bg-red-500 text-white'
                  : isLoading
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'border text-gray-600 hover:bg-gray-50'
              }`}
              style={!isListening && !isLoading ? { borderColor: palette.accent } : {}}
              title={isListening ? 'Stop recording' : 'Start voice input'}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
            {/* Send Button */}
            <button
              onClick={() => handleSendMessage()}
              disabled={!inputValue.trim() || isLoading || !conversationId}
              className={`px-5 py-2 rounded-lg font-medium transition-colors ${
                !inputValue.trim() || isLoading || !conversationId
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'text-white hover:opacity-90'
              }`}
              style={!inputValue.trim() || isLoading || !conversationId ? {} : { backgroundColor: palette.primary }}
              title={!conversationId ? 'Waiting for connection...' : ''}
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          {/* Configuration Info - smaller font */}
          {chatbot && (
            <div className="mt-1 text-xs text-gray-400 flex gap-3" style={{ fontSize: '0.8rem' }}>
              <span>Using: {chatbot.current_llm_name}</span>
              <span>Temperature: {chatbot.temperature}</span>
              <span>Template: {chatbot.template_name || 'Default'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StandaloneChatbot;