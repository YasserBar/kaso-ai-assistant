'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Bot, User, ExternalLink } from 'lucide-react';
import { streamChat } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';
import { useLanguage } from '@/lib/LanguageContext';

interface ChatInterfaceProps {
    conversationId: string | null;
    onConversationChange: (id: string) => void;
    initialMessages?: ChatMessage[];
}

/**
 * ChatInterface Component
 * 
 * Main chat area handling message history, real-time streaming responses,
 * and user input. Uses the RAG API for generating answers.
 */
export default function ChatInterface({
    conversationId,
    onConversationChange,
    initialMessages = []
}: ChatInterfaceProps) {
    const { t } = useLanguage();

    // Core State
    const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // Streaming State
    const [sources, setSources] = useState<string[]>([]);
    const [streamingContent, setStreamingContent] = useState('');

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Scroll to bottom when messages change
    // Auto-scroll to bottom facilitates real-time reading
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => {
        scrollToBottom();
    }, [messages, streamingContent, scrollToBottom]);

    // Sync local state when conversation switches
    useEffect(() => {
        setMessages(initialMessages);
    }, [initialMessages]);

    // Handle message submission and stream management
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!input.trim() || isLoading) return;

        const userMessage: ChatMessage = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: input.trim(),
            createdAt: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);
        setStreamingContent('');
        setSources([]);

        try {
            let fullContent = '';
            let newConversationId = conversationId;

            for await (const event of streamChat(userMessage.content, conversationId || undefined)) {
                switch (event.type) {
                    case 'token':
                        fullContent += event.data;
                        setStreamingContent(fullContent);
                        break;
                    case 'sources':
                        setSources(event.data);
                        break;
                    case 'done':
                        newConversationId = event.data;
                        if (newConversationId && newConversationId !== conversationId) {
                            onConversationChange(newConversationId);
                        }
                        break;
                    case 'error':
                        console.error('Stream error:', event.data);
                        fullContent = `Error: ${event.data}`;
                        break;
                }
            }

            // Add assistant message
            const assistantMessage: ChatMessage = {
                id: `msg-${Date.now()}`,
                role: 'assistant',
                content: fullContent,
                createdAt: new Date(),
            };

            setMessages(prev => [...prev, assistantMessage]);
            setStreamingContent('');

        } catch (error) {
            console.error('Chat error:', error);
            const errorMessage: ChatMessage = {
                id: `error-${Date.now()}`,
                role: 'assistant',
                content: t('error_msg'),
                createdAt: new Date(),
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    // Handle textarea keydown
    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    // Auto-resize textarea
    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value);
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
    };

    return (
        <div className="flex flex-col h-full">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 && !streamingContent && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
                        <Bot className="w-16 h-16 mb-4 text-primary" />
                        <h2 className="text-xl font-semibold mb-2">{t('welcome_title')}</h2>
                        <p className="text-center max-w-md">
                            {t('welcome_desc')}
                        </p>
                        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                            <button
                                onClick={() => setInput(t('ex_what_is'))}
                                className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                            >
                                {t('ex_what_is')}
                            </button>
                            <button
                                onClick={() => setInput(t('ex_who_founded'))}
                                className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                            >
                                {t('ex_who_founded')}
                            </button>
                            <button
                                onClick={() => setInput(t('ex_services'))}
                                className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                            >
                                {t('ex_services')}
                            </button>
                            <button
                                onClick={() => setInput(t('ex_funding'))}
                                className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                            >
                                {t('ex_funding')}
                            </button>
                        </div>
                    </div>
                )}

                {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                ))}

                {/* Streaming response */}
                {streamingContent && (
                    <div className="flex gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="flex-1 bg-white dark:bg-gray-800 rounded-2xl rounded-tl-none p-4 shadow-sm">
                            <div className="prose dark:prose-invert max-w-none">
                                {streamingContent}
                                <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
                            </div>
                        </div>
                    </div>
                )}

                {/* Loading indicator */}
                {isLoading && !streamingContent && (
                    <div className="flex gap-3">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                            <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="bg-white dark:bg-gray-800 rounded-2xl rounded-tl-none p-4 shadow-sm">
                            <Loader2 className="w-5 h-5 animate-spin text-primary" />
                        </div>
                    </div>
                )}

                {/* Sources section removed as per user request */}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900">
                <form onSubmit={handleSubmit} className="flex gap-3">
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyDown}
                        placeholder={t('input_placeholder')}
                        rows={1}
                        className="flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800 px-4 py-3 text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="flex-shrink-0 w-12 h-12 rounded-xl bg-primary text-white flex items-center justify-center hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition"
                    >
                        {isLoading ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Send className="w-5 h-5" />
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}

// Message Bubble Component
function MessageBubble({ message }: { message: ChatMessage }) {
    const isUser = message.role === 'user';

    return (
        <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-gray-700' : 'bg-primary'
                }`}>
                {isUser ? (
                    <User className="w-5 h-5 text-white" />
                ) : (
                    <Bot className="w-5 h-5 text-white" />
                )}
            </div>
            <div className={`flex-1 max-w-[80%] ${isUser ? 'text-end' : ''}`}>
                <div className={`inline-block rounded-2xl p-4 shadow-sm ${isUser
                    ? 'bg-primary text-white rounded-tr-none'
                    : 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-tl-none'
                    }`}>
                    <div className="prose dark:prose-invert max-w-none whitespace-pre-wrap">
                        {message.content}
                    </div>
                </div>
            </div>
        </div>
    );
}
