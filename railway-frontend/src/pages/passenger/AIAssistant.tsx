import { useState, useRef, useEffect } from 'react';
import { assistantAPI } from '../../services/api';

interface Message {
  id: string;
  role: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

const SUGGESTIONS = [
  'Will my train from Delhi to Mumbai be delayed today?',
  'Which route is less congested between Delhi and Chennai?',
  'What is the confirmation probability for WL 15?',
  'Which stations have the highest crowd levels?',
  'Show me the most reliable trains from Kolkata.',
];

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-mono ${
        isUser ? 'bg-rail-cyan/20 text-rail-cyan border border-rail-cyan/30' : 'bg-rail-steel text-rail-ghost border border-white/10'
      }`}>
        {isUser ? 'YOU' : 'AI'}
      </div>

      <div className={`max-w-lg ${isUser ? 'chat-user' : 'chat-ai'} px-4 py-3`}>
        <p className="text-sm leading-relaxed text-white/90">{msg.text}</p>
        <span className="text-xs text-rail-ghost/40 mt-1 block">
          {msg.timestamp.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full bg-rail-steel flex items-center justify-center text-xs font-mono text-rail-ghost border border-white/10">
        AI
      </div>
      <div className="chat-ai px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map(i => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-rail-cyan"
            style={{ animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'ai',
      text: "Hello! I'm the Railway Intelligence Assistant powered by AI. I can help you with train delays, ticket confirmations, congestion analysis, route recommendations, and more. What would you like to know?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = async (text?: string) => {
    const question = text ?? input.trim();
    if (!question) return;

    setInput('');
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      text: question,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const response = await assistantAPI.ask(question);
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: (response as any).answer ?? 'I could not find an answer. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: 'Sorry, I am having trouble connecting to the backend. Please ensure the server is running on port 8000.',
        timestamp: new Date(),
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto h-full flex flex-col" style={{ minHeight: 'calc(100vh - 140px)' }}>
      <div className="mb-5">
        <h1 className="text-2xl font-display tracking-widest text-white mb-1">AI ASSISTANT</h1>
        <p className="text-rail-ghost text-sm">Ask anything about trains, routes, delays, and more</p>
      </div>

      <div className="flex-1 flex flex-col glass rounded-2xl overflow-hidden">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.map(msg => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}
          {isTyping && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Suggestions */}
        {messages.length <= 1 && !isTyping && (
          <div className="px-5 pb-3">
            <p className="text-xs font-mono text-rail-ghost/50 uppercase tracking-wider mb-2">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.slice(0, 3).map(s => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="text-xs px-3 py-1.5 rounded-full glass-light border border-rail-cyan/20 text-rail-ghost hover:text-white hover:border-rail-cyan/40 transition-colors">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="border-t border-white/5 p-4 flex gap-3">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask about delays, ticket confirmations, congestion..."
            className="rail-input flex-1 px-4 py-3 rounded-xl text-sm"
            disabled={isTyping}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || isTyping}
            className="btn-primary px-4 py-3 rounded-xl flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
