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

// UI-friendly Chat Stream Event with 'data' field
export type ChatStreamEvent =
    | { type: 'token'; data: string }
    | { type: 'sources'; data: string[] }
    | { type: 'done'; data: string }
    | { type: 'error'; data: string };

// Raw API response types (snake_case from backend)
export interface ApiConversation {
    id: string;
    title: string;
    preview: string;
    message_count: number;
    created_at: string;
    updated_at: string;
}

export interface ApiMessage {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
}

export interface ApiConversationDetail {
    id: string;
    title: string;
    messages: ApiMessage[];
    created_at: string;
    updated_at: string;
}

export interface ApiConversationsList {
    conversations: ApiConversation[];
    total: number;
    page: number;
    page_size: number;
}

export interface ApiSearchResult {
    conversation_id: string;
    conversation_title: string;
    message_content: string;
    message_role: string;
    relevance_score: number;
    created_at: string;
}

export interface ApiSearchResponse {
    query: string;
    results: ApiSearchResult[];
    total: number;
}
