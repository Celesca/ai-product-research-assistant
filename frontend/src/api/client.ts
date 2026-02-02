import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Types
export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  tools_used?: string[];
  confidence?: number;
  execution_time_ms?: number;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail extends Omit<Conversation, 'message_count'> {
  messages: Message[];
}

export interface QueryResponse {
  status: string;
  response: string;
  products: any[];
  sources: any[];
  tools_used: string[];
  reasoning: string;
  confidence: number;
  execution_time_ms: number;
}

// API Functions
export const createConversation = async (title?: string): Promise<Conversation> => {
  const response = await api.post('/conversations', { title });
  return response.data;
};

export const getConversations = async (limit = 50, offset = 0): Promise<Conversation[]> => {
  const response = await api.get('/conversations', { params: { limit, offset } });
  return response.data.conversations;
};

export const getConversation = async (id: number): Promise<ConversationDetail> => {
  const response = await api.get(`/conversations/${id}`);
  return response.data;
};

export const deleteConversation = async (id: number): Promise<void> => {
  await api.delete(`/conversations/${id}`);
};

export const sendQuery = async (
  query: string,
  conversationId?: number
): Promise<QueryResponse> => {
  const response = await api.post('/query', {
    query,
    conversation_id: conversationId,
  });
  return response.data;
};

export const getHealth = async (): Promise<{ status: string }> => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
