import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Bot, Sparkles, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import { api } from '../api/client';
import type { ChatResponse } from '../types/messwise';

interface MessWiseChatbotProps {
  activeDish: string;
  activeMeal: string;
  activeDate: string;
  activeAttendance?: number;
}

interface MessageItem {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  recommendedAction?: string;
  toolsCalled?: string[];
  data?: Record<string, any>;
  timestamp: string;
}

const QUICK_QUESTIONS = [
  'How much rice should we prepare for lunch?',
  'Why are we preparing this quantity?',
  'Is rain expected during lunch?',
  'Which dish is likely to have the most leftovers today?',
  'What did we learn from past meals?',
  'How much rice if only 400 students attend?',
];

export const MessWiseChatbot: React.FC<MessWiseChatbotProps> = ({
  activeDish,
  activeMeal,
  activeDate,
  activeAttendance,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<MessageItem[]>([
    {
      id: 'welcome_1',
      sender: 'bot',
      text: `Hello! I am Ask MessWise, your AI kitchen assistant. Ask me anything about demand forecasts, recipe quantities, weather advisories, or leftover prevention for ${activeMeal}.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || inputMessage).trim();
    if (!query || loading) return;

    const userMsg: MessageItem = {
      id: `u_${Date.now()}`,
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setLoading(true);

    try {
      const resp: ChatResponse = await api.sendMessWiseChat({
        message: query,
        food_item: activeDish,
        meal: activeMeal,
        date: activeDate,
        attendance: activeAttendance,
      });

      const botMsg: MessageItem = {
        id: `b_${Date.now()}`,
        sender: 'bot',
        text: resp.reply,
        recommendedAction: resp.recommended_action,
        toolsCalled: resp.tools_called,
        data: resp.data,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errorMsg: MessageItem = {
        id: `err_${Date.now()}`,
        sender: 'bot',
        text: `Unable to connect to assistant: ${err.message || 'Please check backend server'}.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        type="button"
        className="messwise-chat-fab"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open Ask MessWise AI Chatbot"
      >
        <span className="fab-icon-wrap">
          {isOpen ? <X size={24} /> : <MessageSquare size={24} />}
        </span>
        <span className="fab-label">Ask MessWise</span>
        <span className="fab-pulse" />
      </button>

      {/* Floating Chat Modal / Drawer */}
      {isOpen && (
        <div className="messwise-chat-panel">
          {/* Header */}
          <div className="chat-panel-header">
            <div className="header-brand">
              <div className="bot-avatar">
                <Bot size={20} />
              </div>
              <div>
                <h3 className="header-title">Ask MessWise</h3>
                <p className="header-subtitle">
                  Lightweight AI Kitchen Assistant • {activeMeal} ({activeDish})
                </p>
              </div>
            </div>
            <button
              type="button"
              className="chat-close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
            >
              <X size={18} />
            </button>
          </div>

          {/* Quick Suggestion Chips */}
          <div className="chat-chips-container">
            <div className="chips-scroll">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  className="quick-chip"
                  onClick={() => handleSend(q)}
                  disabled={loading}
                >
                  <Sparkles size={12} className="chip-sparkle" />
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Messages Feed */}
          <div className="chat-messages-feed">
            {messages.map((m) => (
              <div key={m.id} className={`chat-message chat-message--${m.sender}`}>
                <div className="message-bubble">
                  <div className="message-text">{m.text}</div>

                  {/* Action Item Box if present */}
                  {m.recommendedAction && (
                    <div className="message-action-card">
                      <div className="action-tag">
                        <CheckCircle size={14} />
                        <span>Recommended Kitchen Action</span>
                      </div>
                      <p className="action-text">{m.recommendedAction}</p>
                    </div>
                  )}

                  {/* Tools Called Evidence */}
                  {m.toolsCalled && m.toolsCalled.length > 0 && (
                    <div className="message-tools-tag">
                      <span className="tools-label">Agent Tools:</span>
                      {m.toolsCalled.map((tool) => (
                        <span key={tool} className="tool-badge">
                          {tool}
                        </span>
                      ))}
                    </div>
                  )}

                  <span className="message-time">{m.timestamp}</span>
                </div>
              </div>
            ))}

            {loading && (
              <div className="chat-message chat-message--bot">
                <div className="message-bubble message-bubble--loading">
                  <RefreshCw size={16} className="spin-icon" />
                  <span>Consulting kitchen forecasting agents...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <form
            className="chat-input-bar"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              type="text"
              className="chat-text-input"
              placeholder={`Ask about ${activeDish}, rain, attendance, or leftovers...`}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="chat-send-btn"
              disabled={!inputMessage.trim() || loading}
              aria-label="Send message"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      )}
    </>
  );
};
