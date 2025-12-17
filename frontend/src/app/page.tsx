'use client';

import { useState, useEffect, useCallback } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatInterface from '@/components/ChatInterface';
import { fetchConversation } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';

export default function Home() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Load conversation messages when ID changes
  const loadConversation = useCallback(async (id: string) => {
    try {
      const data = await fetchConversation(id);
      setMessages(data.messages);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      setMessages([]);
    }
  }, []);

  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId, loadConversation]);

  // Handle new conversation
  const handleNewConversation = () => {
    setConversationId(null);
    setMessages([]);
  };

  // Handle conversation change from chat
  const handleConversationChange = (id: string) => {
    setConversationId(id);
    // Trigger sidebar refresh to show new conversation
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar */}
      <Sidebar
        currentConversationId={conversationId}
        onSelectConversation={setConversationId}
        onNewConversation={handleNewConversation}
        refreshTrigger={refreshTrigger}
      />

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        <ChatInterface
          conversationId={conversationId}
          onConversationChange={handleConversationChange}
          initialMessages={messages}
        />
      </main>
    </div>
  );
}
