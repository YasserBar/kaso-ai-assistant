'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    MessageSquare,
    Plus,
    Search,
    Trash2,
    X,
    Menu,
    Moon,
    Sun
} from 'lucide-react';
import { fetchConversations, deleteConversation, searchConversations } from '@/lib/api';
import type { ConversationSummary } from '@/lib/types';
import { useTheme } from 'next-themes';
import { useLanguage } from '@/lib/LanguageContext';

interface SidebarProps {
    currentConversationId: string | null;
    onSelectConversation: (id: string | null) => void;
    onNewConversation: () => void;
    refreshTrigger?: number;
}

/**
 * Sidebar Component
 * 
 * Displays the main navigation, conversation history, and global settings.
 * Features:
 * - Conversation list with search and delete capability
 * - Theme toggle (Dark/Light)
 * - Language switcher (English/Arabic/German)
 * - Mobile responsive layout
 */
export default function Sidebar({
    currentConversationId,
    onSelectConversation,
    onNewConversation,
    refreshTrigger = 0,
}: SidebarProps) {
    const { theme, setTheme } = useTheme();
    const { language, setLanguage, t } = useLanguage();
    const [conversations, setConversations] = useState<ConversationSummary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    // Removed unused isSearching state to satisfy ESLint
    // const [isSearching, setIsSearching] = useState(false);
    const [isMobileOpen, setIsMobileOpen] = useState(false);
    const [mounted, setMounted] = useState(false);

    // Initial mount effect
    useEffect(() => {
        setMounted(true);
    }, []);

    // Load conversations
    const loadConversations = useCallback(async () => {
        try {
            setIsLoading(true);
            const data = await fetchConversations();
            setConversations(data.conversations);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        loadConversations();
    }, [loadConversations, refreshTrigger]);

    // Search conversations
    const handleSearch = async (query: string) => {
        setSearchQuery(query);

        if (!query.trim()) {
            loadConversations();
            return;
        }

        try {
            // setIsSearching(true); // removed unused state
            const results = await searchConversations(query);
            // Convert search results to conversation summaries
            const uniqueConvs = new Map<string, ConversationSummary>();
            results.results.forEach(hit => {
                if (!uniqueConvs.has(hit.conversationId)) {
                    uniqueConvs.set(hit.conversationId, {
                        id: hit.conversationId,
                        title: hit.conversationTitle,
                        preview: hit.messageContent,
                        messageCount: 0,
                        createdAt: hit.createdAt,
                        updatedAt: hit.createdAt,
                    });
                }
            });
            setConversations(Array.from(uniqueConvs.values()));
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            // setIsSearching(false); // removed unused state
        }
    };

    // Delete conversation
    const handleDelete = async (id: string, e: React.MouseEvent) => {
        e.stopPropagation();

        if (!confirm('Are you sure you want to delete this conversation?')) {
            return;
        }

        try {
            await deleteConversation(id);
            setConversations(prev => prev.filter(c => c.id !== id));
            if (currentConversationId === id) {
                onSelectConversation(null);
            }
        } catch (error) {
            console.error('Failed to delete conversation:', error);
        }
    };

    // Format date (client-side only to prevent hydration mismatch)
    const formatDate = (date: Date) => {
        if (!mounted) return '';
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return t('today');
        if (days === 1) return t('yesterday');
        if (days < 7) return `${days} ${t('days_ago')}`;
        return date.toLocaleDateString();
    };

    const sidebarContent = (
        <>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                            src="/kaso_logo.png"
                            alt="Kaso Logo"
                            className="h-8 w-auto object-contain"
                            onError={(e) => {
                                e.currentTarget.style.display = 'none';
                            }}
                        />
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                            Kaso
                        </h1>
                    </div>
                    <button
                        onClick={() => setIsMobileOpen(false)}
                        className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* New Chat Button */}
                <button
                    onClick={() => {
                        onNewConversation();
                        setIsMobileOpen(false);
                    }}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg hover:opacity-90 transition font-medium"
                >
                    <Plus className="w-5 h-5" />
                    {t('new_chat')}
                </button>

                {/* Search */}
                <div className="mt-3 relative">
                    <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-gray-400" />
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => handleSearch(e.target.value)}
                        placeholder={t('search_placeholder')}
                        className="w-full ps-10 pe-4 py-2 bg-gray-100 dark:bg-gray-800 border-0 rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => {
                                setSearchQuery('');
                                loadConversations();
                            }}
                            className="absolute end-3 top-1/2 -translate-y-1/2"
                        >
                            <X className="w-4 h-4 text-gray-400 hover:text-gray-600" />
                        </button>
                    )}
                </div>
            </div>

            {/* Conversations List */}
            <div className="flex-1 overflow-y-auto p-2">
                {isLoading ? (
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full" />
                    </div>
                ) : conversations.length === 0 ? (
                    <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p className="text-sm">{t('no_conversations')}</p>
                        <p className="text-xs mt-1">{t('start_new_chat')}</p>
                    </div>
                ) : (
                    <div className="space-y-1">
                        {conversations.map((conv) => (
                            <div
                                key={conv.id}
                                role="button"
                                tabIndex={0}
                                onClick={() => {
                                    onSelectConversation(conv.id);
                                    setIsMobileOpen(false);
                                }}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        onSelectConversation(conv.id);
                                        setIsMobileOpen(false);
                                    }
                                }}
                                className={`w-full text-start p-3 rounded-lg group transition cursor-pointer ${currentConversationId === conv.id
                                    ? 'bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800'
                                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                                    }`}
                            >
                                <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-sm text-gray-900 dark:text-white truncate">
                                            {conv.title}
                                        </p>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-1">
                                            {conv.preview || 'No messages'}
                                        </p>
                                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                                            {formatDate(conv.updatedAt)}
                                        </p>
                                    </div>
                                    <button
                                        onClick={(e) => handleDelete(conv.id, e)}
                                        className="opacity-0 group-hover:opacity-100 p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition focus:opacity-100"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Settings Footer */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 space-y-3">
                {/* Theme Toggle */}
                <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('theme')}</span>
                    <button
                        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                        className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                        aria-label="Toggle theme"
                    >
                        {mounted && theme === 'dark' ? (
                            <Moon className="w-4 h-4 text-primary" />
                        ) : mounted ? (
                            <Sun className="w-4 h-4 text-orange-500" />
                        ) : (
                            <div className="w-4 h-4" /> // Placeholder to prevent layout shift
                        )}
                    </button>
                </div>

                {/* Language Segmented Control (En/Ar/De) */}
                <div className="space-y-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300 block">{t('language')}</span>
                    <div className="grid grid-cols-3 gap-1 bg-gray-100 dark:bg-gray-800 p-1 rounded-lg">
                        {(['en', 'ar', 'de'] as const).map((lang) => (
                            <button
                                key={lang}
                                onClick={() => setLanguage(lang)}
                                className={`
                                    px-2 py-1.5 rounded-md text-sm font-medium transition-all
                                    ${language === lang
                                        ? 'bg-white dark:bg-gray-700 text-primary shadow-sm'
                                        : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                                    }
                                `}
                            >
                                {lang === 'en' ? 'En' : lang === 'ar' ? 'عربي' : 'De'}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

        </>
    );

    return (
        <>
            {/* Mobile toggle button */}
            <button
                onClick={() => setIsMobileOpen(true)}
                className="lg:hidden fixed top-4 start-4 z-40 p-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg text-gray-700 dark:text-gray-200"
            >
                <Menu className="w-6 h-6" />
            </button>

            {/* Mobile overlay */}
            {isMobileOpen && (
                <div
                    className="lg:hidden fixed inset-0 bg-black/50 z-40"
                    onClick={() => setIsMobileOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside
                className={`
          fixed lg:static inset-y-0 start-0 z-50
          w-80 bg-white dark:bg-gray-900 border-e border-gray-200 dark:border-gray-700
          flex flex-col
          transform transition-transform duration-300
          ${isMobileOpen ? '!translate-x-0' : 'lg:!translate-x-0 ltr:-translate-x-full rtl:translate-x-full'}
        `}
            >
                {sidebarContent}
            </aside>
        </>
    );
}
