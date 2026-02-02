import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatInterface } from './components/ChatInterface';
import {
  createConversation,
  getConversations,
  getConversation,
  deleteConversation,
  sendQuery,
  type Conversation,
  type Message,
} from './api/client';

function App() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const data = await getConversations();
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = useCallback(async (id: number) => {
    try {
      const data = await getConversation(id);
      setMessages(data.messages);
      setActiveConversationId(id);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  }, []);

  const handleNewChat = async () => {
    setActiveConversationId(null);
    setMessages([]);
  };

  const handleSelectConversation = (id: number) => {
    loadConversation(id);
  };

  const handleDeleteConversation = async (id: number) => {
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConversationId === id) {
        setActiveConversationId(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const handleSendMessage = async (content: string) => {
    setIsLoading(true);

    try {
      let conversationId = activeConversationId;

      // Create new conversation if needed
      if (!conversationId) {
        const newConversation = await createConversation();
        conversationId = newConversation.id;
        setActiveConversationId(conversationId);
        setConversations((prev) => [newConversation, ...prev]);
      }

      // Add user message to UI immediately
      const userMessage: Message = {
        id: Date.now(),
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send query to backend
      const response = await sendQuery(content, conversationId);

      // Add assistant response
      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        tools_used: response.tools_used,
        confidence: response.confidence,
        execution_time_ms: response.execution_time_ms,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // Refresh conversations list to update titles
      loadConversations();
    } catch (error) {
      console.error('Failed to send message:', error);
      // Add error message
      const errorMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onDeleteConversation={handleDeleteConversation}
      />
      <ChatInterface
        messages={messages}
        isLoading={isLoading}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}

export default App;
