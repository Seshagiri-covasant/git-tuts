import axios from 'axios';
import { SmartErrorHandler } from '../utils/errorHandler';

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:5000' : 'http://localhost:5000';
//const API_BASE_URL = "https://cognibot-backend-273497745552.us-central1.run.app";

console.log('Environment:', import.meta.env);
console.log('API Base URL:', API_BASE_URL);

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000000, // 5 minutes timeout
});

// Add request interceptor for better error handling
api.interceptors.request.use(
  config => {
    // Add request timestamp for tracking
    (config as any).metadata = { startTime: new Date() };
    return config;
  },
  error => {
    SmartErrorHandler.logError(error, 'Request Interceptor');
    return Promise.reject(error);
  }
);

// Add response interceptor for better error handling
api.interceptors.response.use(
  response => {
    // Log successful requests for debugging
    const duration = new Date().getTime() - (response.config as any).metadata?.startTime;
    if (duration > 5000) { // Log slow requests
      console.warn(`Slow API request: ${response.config.url} took ${duration}ms`);
    }
    return response;
  },
  error => {
    // Don't log 404s for interactions endpoint as they're expected for new conversations
    if (!(error.response?.status === 404 && error.config?.url?.includes('/interactions'))) {
      SmartErrorHandler.logError(error, 'Response Interceptor');
    }
    return Promise.reject(error);
  }
);

// Database Configuration
export const configureMainDatabase = async (config:any) => {
  return api.post('/api/config/database', config);
};

// Chatbot Management
export const getChatbots = async () => {
  try {
    const response = await api.get('/api/chatbots');
    return response;
  } catch (error) {
    throw error;
  }
};

export const createChatbot = async (name:any, temperature?: number) => {
  const payload: any = { name };
  if (temperature !== undefined) {
    payload.temperature = temperature;
  }
  return api.post('/api/chatbots', payload);
};

export const getChatbot = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}`);
};

export const deleteChatbot = async (chatbotId:any) => {
  return api.delete(`/api/chatbots/${chatbotId}`);
};
export const activateForReady = async (chatbotId: any) => {
  return api.post(`/api/chatbots/${chatbotId}/ready`);
};
export const configureChatbotDatabase = async (chatbotId:any, config:any) => {
  // Ensure config has the correct structure for BigQuery
  const requestConfig = {
    db_type: config.db_type,
    db_name: config.db_name,
    selected_tables: config.selected_tables || [],
    ...(config.schema_name ? { schema_name: config.schema_name } : {}),
    ...(config.db_type === 'postgresql' && {
      username: config.username,
      password: config.password,
      host: config.host,
      port: config.port,
      ...(config.schema_name ? { schema_name: config.schema_name } : {}),
    }),
    ...(config.db_type === 'mysql' && {
      username: config.username,
      password: config.password,
      host: config.host,
      port: config.port,
      ...(config.schema_name ? { schema_name: config.schema_name } : {}),
    }),
    ...(config.db_type === 'mssql' && {
      username: config.username,
      password: config.password,
      host: config.host,
      port: config.port,
      driver: config.driver,
      ...(config.schema_name ? { schema_name: config.schema_name } : {}),
    }),
    ...(config.db_type === 'bigquery' && {
      project_id: config.project_id,
      dataset_id: config.dataset_id,
      credentials_json: config.credentials_json,
      ...(config.schema_name ? { schema_name: config.schema_name } : {}),
    }),
  };
  
  return api.post(`/api/chatbots/${chatbotId}/database`, requestConfig);
};

export const startBenchmark = async (chatbotId:any, temperature?: number) => {
  const payload: any = {};
  if (temperature !== undefined) {
    payload.temperature = temperature;
  }
  return api.post(`/api/chatbots/${chatbotId}/benchmark`, payload);
};

export const getBenchmarkStatus = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}/benchmark`);
};

export const getBenchmarkDetails = async (chatbotId:any, llm_name?: string, temperature?: number) => {
  const params = new URLSearchParams();
  if (llm_name) params.append('llm_name', llm_name);
  if (temperature !== undefined) params.append('temperature', temperature.toString());
  return api.get(`/api/chatbots/${chatbotId}/benchmark/details?${params}`);
};

export const cleanupBenchmarkData = async (chatbotId: string) => {
  return api.post(`/api/chatbots/${chatbotId}/benchmark/cleanup`);
};

// ========== CUSTOM TEST SUITE API FUNCTIONS ==========

export const createCustomTest = async (chatbotId: string, testData: {
  test_name: string;
  original_sql: string;
  natural_question: string;
}) => {
  return api.post(`/api/chatbots/${chatbotId}/custom-tests`, testData);
};

export const getCustomTests = async (chatbotId: string, testName?: string) => {
  const params = new URLSearchParams();
  if (testName) params.append('test_name', testName);
  return api.get(`/api/chatbots/${chatbotId}/custom-tests?${params}`);
};

export const getCustomTestSuites = async (chatbotId: string) => {
  return api.get(`/api/chatbots/${chatbotId}/custom-tests/suites`);
};

export const runCustomTests = async (chatbotId: string, options?: {
  test_name?: string;
  temperature?: number;
}) => {
  return api.post(`/api/chatbots/${chatbotId}/custom-tests/run`, options || {});
};

export const getCustomTestMetrics = async (chatbotId: string, options?: {
  test_name?: string;
  llm_used?: string;
}) => {
  const params = new URLSearchParams();
  if (options?.test_name) params.append('test_name', options.test_name);
  if (options?.llm_used) params.append('llm_used', options.llm_used);
  return api.get(`/api/chatbots/${chatbotId}/custom-tests/metrics?${params}`);
};

export const deleteCustomTest = async (testId: string) => {
  return api.delete(`/api/custom-tests/${testId}`);
};

export const getPerformanceMetrics = (chatbotId: string, llmName?: string, temperature?: number) => {
  let url = `/api/chatbots/${chatbotId}/performance`;
  const params = new URLSearchParams();
  
  if (llmName) {
    params.append('llm_name', llmName);
  }
  if (temperature !== undefined) {
    params.append('temperature', temperature.toString());
  }
  
  if (params.toString()) {
    url += `?${params.toString()}`;
  }
  
  return api.get(url);
};

// Conversation Management
export const createConversation = async (chatbotId:any, name = "New Conversation", owner = "user") => {
  try {
    const payload = {
      conversation_name: name,
      owner,
     
    };

    const response = await api.post(`/api/chatbots/${chatbotId}/conversations`, payload);
    return response;
  } catch (error) {
    throw error;
  }
};

export const getAllConversations = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}/conversations`, {
    params: { chatbot_id: chatbotId }
  });
};

export const getConversation = async (conversationId:any) => {
  return api.get(`/api/conversations/${conversationId}`);
};
export const getQuery = async (conversationId:any,interactionsId:any) => {
  return api.get(`/api/conversations/${conversationId}/interactions/${interactionsId}`);
};
export const getChatbotDetails = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}`);
};

export const deleteConversation = async (chatbotId:any, conversationId:any) => {
  return api.delete(`/api/conversations/${conversationId}`);
};

// Interaction Management
export const createInteraction = async (conversationId:any, message:any, llmName?: string) => {
  const payload: any = { request: message };
  if (llmName) payload.llm_name = llmName;
  const response = await api.post(`/api/conversations/${conversationId}/interactions`, payload);
  return response.data; // Returns final_result, cleaned_query, result_meta?, ba_summary
};

// New: interaction result pagination
export const getInteractionResultMeta = async (interactionId: string) => {
  const response = await api.get(`/api/interactions/${interactionId}/result/meta`);
  return response.data;
};

export const getInteractionResultPage = async (interactionId: string, page: number) => {
  const response = await api.get(`/api/interactions/${interactionId}/result/pages`, { params: { page } });
  return response.data;
};

export const getConversationInteractionCount = async (conversationId: string, chatbotId: string) => {
  try {
    const response = await api.get(`/api/conversations/${conversationId}/interaction-count?chatbot_id=${chatbotId}`);
    return response;
  } catch (error) {
    throw error;
  }
};

export const getAllInteractions = async (conversationId:any,limit:any,offset:any,chatbotId:any) => {
  try {
    const response = await api.get(`/api/conversations/${conversationId}/interactions?limit=${limit}&offset=${offset}&chatbot_id=${chatbotId}`);
    return response;
  } catch (error) {
    throw error;
  }
};

// Processing Status
export const getConversationStatus = async (conversationId: string) => {
  try {
    const response = await api.get(`/api/conversations/${conversationId}/status`);
    return response;
  } catch (error) {
    throw error;
  }
};

// Debug Information
export const getDebugInformation = async (conversationId: string, interactionId: string) => {
  try {
    const response = await api.get(`/api/interactions/${interactionId}/debug`, {
      params: { conversation_id: conversationId }
    });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// LLM Settings
export const setLLMSettings = async (chatbotId:any, llmName:any, temperature?: number) => {
  const payload: any = { llm_name: llmName };
  if (temperature !== undefined) {
    payload.temperature = temperature;
  }
  return api.post(`/api/chatbots/${chatbotId}/llm`, payload);
};

export const updateLLMSettings = async (chatbotId:any, llmName:any, temperature?: number) => {
  const payload: any = { llm_name: llmName };
  if (temperature !== undefined) {
    payload.temperature = temperature;
  }
  return api.put(`/api/chatbots/${chatbotId}/llm`, payload);
};



// Schema Management
export const getChatbotSchema = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}/schema`);
};

// Template Management
export const getAllTemplates = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}/templates`, );
};

export const createTemplate = async (chatbotId:any, body:any) => {
  return api.post(`/api/chatbots/${chatbotId}/template`,body);
};

export const updateTemplate = async (chatbotId:any, templateId:any, template:any) => {
  return api.put(`/api/chatbots/${chatbotId}/template`, template);
};

export const getChatbotTemplate = async (chatbotId:any) => {
  return api.get(`/api/chatbots/${chatbotId}/template`);
};

export const getTemplate = async (chatbotId:any, templateId:any) => {
  return api.get(`/api/templates/${templateId}`, {
    params: { chatbot_id: chatbotId }
  });
};

export const deleteTemplate = async (chatbotId:any, templateId:any) => {
  return api.delete(`/api/templates/${templateId}`, {
    params: { chatbot_id: chatbotId }
  });
};

// Chatbot Management
export const restartChatbot = async (chatbotId:any) => {
  return api.post(`/api/chatbots/${chatbotId}/restart`);
};

// Health Check
export const checkHealth = async () => {
  return api.get('/api/health');
};

// Metrics
export const getMetrics = async () => {
  return api.get('/api/metrics');
};
export const getStatusName=(name:string)=>{
switch(name){
  case 'created':
    return 'Created';
  case 'ready':
    return 'Ready';
    case 'db_configured':
    return 'DB Configured';
    case 'llm_configured':
    return 'LLM Configured';
     case 'template_configured':
    return 'Template Configured';
  default:
    return name;
}}
 
export const getDBgetName=(name:string)=>{
switch(name){
  case 'COHERE':
    return 'Cohere';
  case 'CHATGPT-4O-MINI':
    return 'ChatGPT-4O Mini';
    case 'AZURE_CHATGPT-4O-MINI':
    return 'Azure ChatGPT-4O Mini';
    case 'AZURE':
    return 'Azure ChatGPT-4o Mini';
  default:
    return name;
}}

// Rating Management
export const rateInteraction = async (conversationId: string, interactionId: string, rating: number) => {
  try {
    const response = await api.post(`/api/conversations/${conversationId}/interactions/${interactionId}/rating`, {
      rating
    });
    return response;
  } catch (error) {
    throw error;
  }
};

export const getInteractionRating = async (conversationId: string, interactionId: string) => {
  try {
    const response = await api.get(`/api/conversations/${conversationId}/interactions/${interactionId}/rating`);
    return response;
  } catch (error) {
    throw error;
  }
};

// Global Template Management
export const getTemplates = async (params?: any) => {
  return api.get('/api/templates', { params });
};

export const createGlobalTemplate = async (template: any) => {
  return api.post('/api/templates', template);
};

export const getGlobalTemplate = async (templateId: number) => {
  return api.get(`/api/templates/${templateId}`);
};

export const updateGlobalTemplate = async (templateId: number, template: any) => {
  return api.put(`/api/templates/${templateId}`, template);
};

export const deleteGlobalTemplate = async (templateId: number) => {
  return api.delete(`/api/templates/${templateId}`);
};

export const previewGlobalTemplate = async (templateId: number, data: any) => {
  return api.post(`/api/templates/${templateId}/preview`, data);
};

// BA Insights and Visualization
export const getBAInsights = async (table: any[], prompt: string = "", chatbotId: string, interactionId?: string, regenerate?: boolean) => {
  if (!chatbotId) {
    throw new Error('chatbotId is required for BA insights');
  }
  const payload: any = { table, prompt, chatbot_id: chatbotId };
  if (interactionId) payload.interaction_id = interactionId;
  if (regenerate === true) payload.regenerate = true;
  console.log('getBAInsights API call payload:', payload);
  return api.post('/api/ba-insights', payload);
};

export const getVisualization = async (table: any[], prompt: string = "", sqlQuery: string = "", chatbotId: string) => {
  if (!chatbotId) {
    throw new Error('chatbotId is required for visualization');
  }
  const payload = { table, prompt, sql_query: sqlQuery, chatbot_id: chatbotId };
  console.log('getVisualization API call payload:', payload);
  return api.post('/api/visualize', payload);
};

// Database Schema Update
export const updateDatabaseSchema = async (chatbotId: string) => {
  return api.post(`/api/chatbots/${chatbotId}/database/update-schema`);
};

// Semantic Schema Management
export const getSemanticSchema = async (chatbotId: string) => {
  return api.get(`/api/chatbots/${chatbotId}/semantic-schema`);
};

export const updateSemanticSchema = async (chatbotId: string, semanticSchema: any) => {
  return api.put(`/api/chatbots/${chatbotId}/semantic-schema`, {
    semantic_schema: semanticSchema
  });
};

// Export semantic schema as CSV
export const exportSemanticSchema = async (chatbotId: string) => {
  const response = await api.get(`/api/chatbots/${chatbotId}/semantic-schema/export`, {
    responseType: 'blob'
  });
  
  // Create download link
  const blob = new Blob([response.data], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `schema_${chatbotId}_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
  
  return response;
};

// Import semantic schema from CSV
export const importSemanticSchema = async (chatbotId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  
  return api.post(`/api/chatbots/${chatbotId}/semantic-schema/import`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};



export const updateKnowledgeBaseSettings = async (chatbotId: string, knowledgeBaseData: {
  industry: string;
  vertical: string;
  domain: string;
  knowledge_base_file?: string;
}) => {
  return api.post(`/api/chatbots/${chatbotId}/knowledge-base`, knowledgeBaseData);
};

export default api; 