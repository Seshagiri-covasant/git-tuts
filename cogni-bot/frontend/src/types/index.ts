export interface Chatbot {
  chatbot_id: string;
  name: string;
    type: 'PostgreSQL' |'SQLite' | 'BigQuery';
    host: string;
    port: number;
    database: string;
    llm_name: string;
  created_at: string;
  db_url:'',
  template_name:'',
  status: 'ready' | 'created' | 'llm_configured' | 'template_configured';
  current_llm_name?: string;
  temperature?: number;
  // BigQuery specific fields
  project_id?: string;
  dataset_id?: string;
  credentials_json?: string;
}


export interface Conversation {
  id: string;
  chatbotId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
  conversationName: string;
  conversationId: string;
  startTime: string;
  conversationType?: string;
  owner?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface LLMSettings {
  model: string;
  temperature: number;
  maxTokens: number;
  topP: number;
  frequencyPenalty: number;
  presencePenalty: number;
}

export interface InteractionResultMeta {
  interaction_id: string;
  total_rows: number;
  total_columns: number;
  columns: string[];
  page_size: number;
  has_tabular_data: boolean;
}

export interface DBSettings {
  provider: string;
  connectionString?: string;
  region?: string;
  saveHistory: boolean;
}

export interface Template {
  id: number;
  name: string;
  description: string;
  content: string;
  owner: string;
  visibility: 'public' | 'private' | 'shared';
  shared_with: string[];
  created_at: string;
  updated_at: string;
  dataset_domain?: string;
}