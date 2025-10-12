import { LLMSettings, DBSettings, Chatbot, Conversation } from '../types';

export const DEFAULT_LLM_SETTINGS: LLMSettings = {
  model: 'gpt-4',
  temperature: 0.7,
  maxTokens: 1000,
  topP: 1,
  frequencyPenalty: 0,
  presencePenalty: 0,
};

export const DEFAULT_DB_SETTINGS: DBSettings = {
  provider: 'supabase',
  region: 'us-east-1',
  saveHistory: true,
};

export const SAMPLE_PROJECTS: Chatbot[] = [
  {
    id: '1',
    name: 'Customer Support Bot',
    description: 'AI assistant for handling customer inquiries',
    createdAt: '2025-03-15T10:30:00Z',
  },
  {
    id: '2',
    name: 'Code Helper',
    description: 'AI assistant for programming help',
    createdAt: '2025-03-10T14:15:00Z',
  },
  {
    id: '3',
    name: 'Content Writer',
    description: 'AI for generating marketing copy',
    createdAt: '2025-03-05T09:45:00Z',
  },
  {
    id: '4',
    name: 'Data Analysis Assistant',
    description: 'AI for data analysis and visualization',
    createdAt: '2025-03-04T08:30:00Z',
  },
  {
    id: '5',
    name: 'Language Tutor',
    description: 'AI language learning assistant',
    createdAt: '2025-03-03T15:20:00Z',
  },
  {
    id: '6',
    name: 'Research Helper',
    description: 'AI for academic research assistance',
    createdAt: '2025-03-02T11:10:00Z',
  },
  {
    id: '7',
    name: 'Legal Assistant',
    description: 'AI for legal document analysis',
    createdAt: '2025-03-01T16:45:00Z',
  },
  {
    id: '8',
    name: 'Healthcare Bot',
    description: 'AI for medical information',
    createdAt: '2025-02-28T13:25:00Z',
  }
];

export const SAMPLE_CONVERSATIONS: Conversation[] = [
  {
    id: '1',
    chatbotId: '1',
    title: 'Refund Process Discussion',
    createdAt: '2025-03-15T11:30:00Z',
    updatedAt: '2025-03-15T11:45:00Z',
    messages: [
      {
        id: '1-1',
        role: 'user',
        content: 'How do I process a refund for my recent order?',
        timestamp: '2025-03-15T11:30:00Z',
      },
      {
        id: '1-2',
        role: 'assistant',
        content: 'To process a refund, please provide your order number and the reason for the refund. Once we have this information, we can initiate the refund process which typically takes 3-5 business days to reflect in your account.',
        timestamp: '2025-03-15T11:31:00Z',
      },
    ],
  },
  {
    id: '2',
    chatbotId: '1',
    title: 'Product Features Inquiry',
    createdAt: '2025-03-14T09:20:00Z',
    updatedAt: '2025-03-14T09:35:00Z',
    messages: [
      {
        id: '2-1',
        role: 'user',
        content: 'What are the main features of your premium plan?',
        timestamp: '2025-03-14T09:20:00Z',
      },
      {
        id: '2-2',
        role: 'assistant',
        content: 'Our premium plan includes unlimited access to all templates, priority customer support, advanced analytics, and the ability to export data in multiple formats. You also get access to exclusive webinars and training materials.',
        timestamp: '2025-03-14T09:21:00Z',
      },
    ],
  },
  {
    id: '3',
    chatbotId: '2',
    title: 'React Hooks Help',
    createdAt: '2025-03-12T16:40:00Z',
    updatedAt: '2025-03-12T17:05:00Z',
    messages: [
      {
        id: '3-1',
        role: 'user',
        content: 'Can you explain how useEffect works in React?',
        timestamp: '2025-03-12T16:40:00Z',
      },
      {
        id: '3-2',
        role: 'assistant',
        content: 'The useEffect hook in React allows you to perform side effects in functional components. Side effects can include data fetching, subscriptions, or manually changing the DOM.\n\nThe basic syntax is:\n\n```jsx\nuseEffect(() => {\n  // Your side effect code here\n  return () => {\n    // Cleanup function (optional)\n  };\n}, [dependencies]);\n```\n\nThe hook takes two arguments:\n1. A function that contains the side effect code\n2. A dependency array that determines when the effect should run\n\nIf the dependency array is empty `[]`, the effect runs only after the initial render. If you include variables in the array, the effect runs whenever any of those variables change.',
        timestamp: '2025-03-12T16:42:00Z',
      },
    ],
  },
  {
    id: '4',
    chatbotId: '1',
    title: 'Shipping Policy Questions',
    createdAt: '2025-03-11T13:15:00Z',
    updatedAt: '2025-03-11T13:30:00Z',
    messages: [
      {
        id: '4-1',
        role: 'user',
        content: 'What is your international shipping policy?',
        timestamp: '2025-03-11T13:15:00Z',
      },
      {
        id: '4-2',
        role: 'assistant',
        content: 'We offer international shipping to over 100 countries. Shipping times vary by location, typically 7-14 business days. All international orders are fully tracked and insured.',
        timestamp: '2025-03-11T13:16:00Z',
      },
    ],
  },
  {
    id: '5',
    chatbotId: '3',
    title: 'Blog Post Ideas',
    createdAt: '2025-03-10T10:20:00Z',
    updatedAt: '2025-03-10T10:45:00Z',
    messages: [
      {
        id: '5-1',
        role: 'user',
        content: 'Generate some blog post ideas about artificial intelligence.',
        timestamp: '2025-03-10T10:20:00Z',
      },
      {
        id: '5-2',
        role: 'assistant',
        content: 'Here are some engaging blog post ideas about AI:\n\n1. "How AI is Revolutionizing Healthcare"\n2. "The Ethics of AI: Navigating the Future"\n3. "AI in Everyday Life: Applications You Might Not Notice"\n4. "Machine Learning vs. Deep Learning: Understanding the Difference"\n5. "The Future of Work: AI and Human Collaboration"',
        timestamp: '2025-03-10T10:21:00Z',
      },
    ],
  },
  {
    id: '6',
    chatbotId: '4',
    title: 'Data Visualization Tips',
    createdAt: '2025-03-09T14:30:00Z',
    updatedAt: '2025-03-09T14:45:00Z',
    messages: [
      {
        id: '6-1',
        role: 'user',
        content: 'What are the best practices for data visualization?',
        timestamp: '2025-03-09T14:30:00Z',
      },
      {
        id: '6-2',
        role: 'assistant',
        content: 'Here are key best practices for effective data visualization:\n\n1. Choose the right chart type for your data\n2. Keep it simple and avoid chart junk\n3. Use color purposefully\n4. Ensure proper scaling and axis labels\n5. Include clear titles and legends\n6. Make it accessible for all users',
        timestamp: '2025-03-09T14:31:00Z',
      },
    ],
  }
];

export const AVAILABLE_LLM_MODELS = [
  { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
  { id: 'gpt-4', name: 'GPT-4' },
  { id: 'gpt-4o', name: 'GPT-4o' },
  { id: 'claude-3-opus', name: 'Claude 3 Opus' },
  { id: 'claude-3-sonnet', name: 'Claude 3 Sonnet' },
  { id: 'llama-3-70b', name: 'Llama 3 70B' },
  { id: 'GEMINI', name: 'Gemini 1.5 Pro' },
];

export const DB_PROVIDERS = [
  { id: 'supabase', name: 'Supabase' },
  { id: 'firebase', name: 'Firebase' },
  { id: 'mongodb', name: 'MongoDB Atlas' },
  { id: 'postgres', name: 'PostgreSQL' },
  { id: 'bigquery', name: 'Google BigQuery' },
];