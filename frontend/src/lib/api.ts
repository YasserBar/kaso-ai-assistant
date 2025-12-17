/**
 * API Client for Kaso AI Assistant
 */

import { API_ENDPOINTS, getApiHeaders } from './config';
import type {
    ConversationList,
    ConversationDetail,
    ConversationSummary,
    SearchResponse,
    ApiConversationsList,
    ApiConversationDetail,
    ApiSearchResponse,
    ChatStreamEvent,
} from './types';

/**
 * Fetch conversations list
 */
export async function fetchConversations(
    page: number = 1,
    pageSize: number = 20
): Promise<ConversationList> {
    const response = await fetch(
        `${API_ENDPOINTS.conversations}?page=${page}&page_size=${pageSize}`,
        { headers: getApiHeaders() }
    );

    if (!response.ok) {
        throw new Error('Failed to fetch conversations');
    }

    const data: ApiConversationsList = await response.json();
    return {
        conversations: data.conversations.map((c) => ({
            id: c.id,
            title: c.title,
            preview: c.preview,
            messageCount: c.message_count,
            createdAt: new Date(c.created_at),
            updatedAt: new Date(c.updated_at),
        })),
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
    };
}

/**
 * Fetch single conversation with messages
 */
export async function fetchConversation(id: string): Promise<ConversationDetail> {
    const response = await fetch(
        API_ENDPOINTS.conversation(id),
        { headers: getApiHeaders() }
    );

    if (!response.ok) {
        throw new Error('Failed to fetch conversation');
    }

    const data: ApiConversationDetail = await response.json();
    return {
        id: data.id,
        title: data.title,
        messages: data.messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            createdAt: new Date(m.created_at),
        })),
        createdAt: new Date(data.created_at),
        updatedAt: new Date(data.updated_at),
    };
}

/**
 * Create new conversation
 */
export async function createConversation(title?: string): Promise<ConversationSummary> {
    const response = await fetch(API_ENDPOINTS.conversations, {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({ title }),
    });

    if (!response.ok) {
        throw new Error('Failed to create conversation');
    }

    const data: ApiConversationDetail = await response.json();
    return {
        id: data.id,
        title: data.title,
        preview: '',
        messageCount: data.messages?.length ?? 0,
        createdAt: new Date(data.created_at),
        updatedAt: new Date(data.updated_at),
    };
}

/**
 * Delete conversation
 */
export async function deleteConversation(id: string): Promise<void> {
    const response = await fetch(API_ENDPOINTS.conversation(id), {
        method: 'DELETE',
        headers: getApiHeaders(),
    });

    if (!response.ok) {
        throw new Error('Failed to delete conversation');
    }
}

/**
 * Search conversations
 */
export async function searchConversations(
    query: string,
    limit: number = 10
): Promise<SearchResponse> {
    const response = await fetch(
        `${API_ENDPOINTS.searchConversations}?query=${encodeURIComponent(query)}&limit=${limit}`,
        { headers: getApiHeaders() }
    );

    if (!response.ok) {
        throw new Error('Failed to search conversations');
    }

    const data: ApiSearchResponse = await response.json();
    return {
        query: data.query,
        results: data.results.map((r) => ({
            conversationId: r.conversation_id,
            conversationTitle: r.conversation_title,
            messageContent: r.message_content,
            messageRole: r.message_role,
            relevanceScore: r.relevance_score,
            createdAt: new Date(r.created_at),
        })),
        total: data.total,
    };
}

/**
 * Stream chat response using SSE
 * Parses 'event' and 'data' lines, yielding typed events for UI consumption.
 */
export async function* streamChat(
    message: string,
    conversationId?: string
): AsyncGenerator<ChatStreamEvent> {
    // Initiate SSE stream via POST; backend emits sources, token, done, error events
    const response = await fetch(API_ENDPOINTS.chatStream, {
        method: 'POST',
        headers: getApiHeaders(),
        body: JSON.stringify({
            message,
            conversation_id: conversationId,
            stream: true,
        }),
    });

    if (!response.ok) {
        throw new Error('Failed to start chat stream');
    }

    const reader = response.body?.getReader();
    if (!reader) {
        throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Accumulate chunk and split by newline; keep remainder in buffer
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        // We expect pairs of event/data lines but only parse 'data' JSON payloads
        for (const line of lines) {
            if (line.startsWith('data:')) {
                const data = line.slice(5).trim();
                if (data) {
                    try {
                        const parsed = JSON.parse(data);
                        // Map backend payload keys to typed events for UI
                        if (parsed.token !== undefined) {
                            yield { type: 'token', data: String(parsed.token) };
                        } else if (parsed.sources !== undefined) {
                            yield { type: 'sources', data: parsed.sources as string[] };
                        } else if (parsed.conversation_id !== undefined) {
                            yield { type: 'done', data: String(parsed.conversation_id) };
                        } else if (parsed.error !== undefined) {
                            yield { type: 'error', data: String(parsed.error) };
                        }
                    } catch (e) {
                        console.error('Failed to parse SSE data:', data, e);
                    }
                }
            }
        }
    }
}
