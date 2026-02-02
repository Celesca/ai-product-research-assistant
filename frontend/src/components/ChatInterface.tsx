import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Bot, User, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Message, QueryResponse } from '../api/client';

interface ChatInterfaceProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${
          isUser
            ? 'bg-gradient-to-br from-indigo-600 to-purple-600'
            : 'bg-gradient-to-br from-emerald-600 to-teal-600'
        }`}
      >
        {isUser ? <User size={20} className="text-white" /> : <Bot size={20} className="text-white" />}
      </div>

      {/* Message Content */}
      <div
        className={`max-w-[75%] px-5 py-4 rounded-2xl ${
          isUser
            ? 'bg-gradient-to-br from-indigo-600 to-purple-600 text-white'
            : 'bg-slate-800/80 backdrop-blur border border-slate-700/50 text-slate-200'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="markdown-content">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}

        {/* Metadata for assistant messages */}
        {!isUser && (message.tools_used?.length || message.confidence) && (
          <div className="mt-3 pt-3 border-t border-slate-700/50 flex flex-wrap gap-2 text-xs">
            {message.tools_used?.map((tool) => (
              <span
                key={tool}
                className="px-2 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
              >
                {tool}
              </span>
            ))}
            {message.confidence && (
              <span className="px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                {Math.round(message.confidence * 100)}% confidence
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatInterface({ messages, isLoading, onSendMessage }: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  return (
    <div className="flex-1 flex flex-col h-screen bg-gradient-to-br from-slate-900 to-slate-950">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center mb-6 shadow-2xl shadow-indigo-500/30">
              <Sparkles size={40} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">
              AI Product Research Assistant
            </h2>
            <p className="text-slate-400 max-w-md mb-8">
              Ask me about products, pricing, market trends, or competitor analysis.
              I can search our catalog, analyze prices, and find web information.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl">
              {[
                'What wireless headphones do we have in stock?',
                'Which products have the lowest profit margins?',
                'Current market price for noise-cancelling headphones?',
                'Should we adjust AudioMax headphones pricing vs competitors?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onSendMessage(suggestion)}
                  className="px-4 py-3 text-left text-sm text-slate-300 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all hover:border-indigo-500/50"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {isLoading && (
          <div className="flex gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-600 to-teal-600 flex items-center justify-center">
              <Bot size={20} className="text-white" />
            </div>
            <div className="px-5 py-4 rounded-2xl bg-slate-800/80 backdrop-blur border border-slate-700/50">
              <div className="flex items-center gap-2 text-slate-400">
                <Loader2 size={16} className="animate-spin" />
                Thinking...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-slate-800">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about products, pricing, or market trends..."
              disabled={isLoading}
              className="flex-1 px-5 py-4 rounded-xl bg-slate-800/80 border border-slate-700/50 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 focus:ring-2 focus:ring-indigo-500/20 transition-all disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="px-6 py-4 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-indigo-500/25"
            >
              {isLoading ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
