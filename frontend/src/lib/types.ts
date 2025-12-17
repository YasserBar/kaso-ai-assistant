/**
 * TypeScript Types for Kaso AI Assistant
 */

// Chat Types
export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    createdAt: Date;
}

export interface ChatRequest {
    message: string;
    conversationId?: string;
    stream?: boolean;
}

export interface ChatResponse {
    message: string;
    conversationId: string;
    sources: string[];
}

// Conversation Types
export interface ConversationSummary {
    id: string;
    title: string;
    preview: string;
    messageCount: number;
    createdAt: Date;
    updatedAt: Date;
}

export interface ConversationDetail {
    id: string;
    title: string;
    messages: ChatMessage[];
    createdAt: Date;
    updatedAt: Date;
}

export interface ConversationList {
    conversations: ConversationSummary[];
    total: number;
    page: number;
    pageSize: number;
}

// Search Types
export interface SearchHit {
    conversationId: string;
    conversationTitle: string;
    messageContent: string;
    messageRole: string;
    relevanceScore: number;
    createdAt: Date;
}

export interface SearchResponse {
    query: string;
    results: SearchHit[];
    total: number;
}

// SSE Event Types
export interface SSETokenEvent {
    type: 'token';
    token: string;
}

export interface SSESourcesEvent {
    type: 'sources';
    sources: string[];
}

export interface SSEDoneEvent {
    type: 'done';
    conversationId: string;
}

export interface SSEErrorEvent {
    type: 'error';
    error: string;
}

export type SSEEvent = SSETokenEvent | SSESourcesEvent | SSEDoneEvent | SSEErrorEvent;
