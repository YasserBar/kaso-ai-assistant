/**
 * API Configuration
 */

// Backend API URL
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// API Key for authentication
export const API_KEY = process.env.NEXT_PUBLIC_API_KEY || '';

/**
 * Default headers for API requests
 */
export function getApiHeaders(): HeadersInit {
    return {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
    };
}

/**
 * API Endpoints
 */
export const API_ENDPOINTS = {
    // Chat
    chatStream: `${API_BASE_URL}/api/chat/stream`,
    chat: `${API_BASE_URL}/api/chat`,

    // Conversations
    conversations: `${API_BASE_URL}/api/conversations`,
    conversation: (id: string) => `${API_BASE_URL}/api/conversations/${id}`,

    // Search
    searchConversations: `${API_BASE_URL}/api/search/conversations`,
    searchKnowledge: `${API_BASE_URL}/api/search/knowledge`,
    search: `${API_BASE_URL}/api/search`,
};
