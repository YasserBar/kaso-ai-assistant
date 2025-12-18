/**
 * API Configuration
 */

// Backend API base (proxy root)
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

// API Key is no longer sent from the browser; the server proxy adds it via API_SECRET_KEY

/**
 * Default headers for API requests (client-side)
 */
export function getApiHeaders(): HeadersInit {
    return {
        'Content-Type': 'application/json',
        // Do NOT send X-API-Key from the browser
    };
}

/**
 * API Endpoints (API_BASE_URL already points to '/api')
 */
export const API_ENDPOINTS = {
    // Chat
    chatStream: `${API_BASE_URL}/chat/stream`,
    chat: `${API_BASE_URL}/chat`,

    // Conversations
    conversations: `${API_BASE_URL}/conversations`,
    conversation: (id: string) => `${API_BASE_URL}/conversations/${id}`,

    // Search
    searchConversations: `${API_BASE_URL}/search/conversations`,
    searchKnowledge: `${API_BASE_URL}/search/knowledge`,
    search: `${API_BASE_URL}/search`,
};
