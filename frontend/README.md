# Kaso AI Assistant - Frontend

Web interface for Kaso AI Assistant built with Next.js and Tailwind CSS.

## Features

- 💬 Chat Interface — Real-time streaming responses (SSE)
- 📜 Conversation History — Browse and search past conversations
- 🔍 Search — Find conversations by keyword
- 📱 Responsive — Works on desktop and mobile
- 🌙 Dark Mode — Automatic dark mode support
- 🌍 RTL Support — Arabic language support
- 🔐 Server-side Proxy — All API calls go through Next.js route handler, secrets never exposed to the browser

## Setup

### Prerequisites

- Node.js 18+
- Docker & Docker Compose
- Backend service exposed at `http://localhost:8000` (via docker-compose)

### Installation

```bash
# Install dependencies
npm install

# Create environment file
# Copy env.example.txt to .env.local and edit:
# NEXT_PUBLIC_API_URL=/api
# NEXT_PUBLIC_API_KEY=your_secret_api_key_here

# Start development server
npm run dev
```

### Environment Variables

- `NEXT_PUBLIC_API_URL`: Proxy base path (default: `/api`). Requests are forwarded via Next.js route handler to the internal backend service.
- `NEXT_PUBLIC_API_KEY`: API key for authentication (must match backend `API_SECRET_KEY`).

Root `.env` (used by docker-compose):
- `API_SECRET_KEY`: Secret key used by the backend and injected by the server-side proxy.
- `CORS_ORIGINS`: Must include the frontend domain (e.g., `http://localhost:3000`).
- `GROQ_API_KEY`: Backend Groq API key (optional).
- `NODE_ENV`: Recommended `production` for Docker runtime.
- `NEXT_PUBLIC_API_URL`: Should be `/api` to use the internal proxy.

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout with fonts
│   ├── page.tsx            # Main chat page (client component)
│   └── globals.css         # Global styles
├── components/
│   ├── ChatInterface.tsx   # Chat messages + input
│   └── Sidebar.tsx         # Conversation history
└── lib/
    ├── api.ts              # API client with SSE streaming
    ├── config.ts           # Configuration (API_BASE_URL = '/api')
    └── types.ts            # TypeScript types
```

## API Integration & Architecture

- SSE Streaming — Real-time token-by-token responses.
- REST API — CRUD operations for conversations and search.
- Server-side Proxy — The Next.js route handler at `/api/*` forwards requests to `http://backend:8000/api/*` internally via Docker network.
- Authentication — The proxy injects `X-API-Key` from server environment; the browser never sends secrets.
- CORS — Backend should allow the frontend origin (e.g., `http://localhost:3000`).

## Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

## Docker

This project supports Docker Compose.

- Ensure the root `.env` is configured with:
  - `NEXT_PUBLIC_API_URL=/api`
  - `NEXT_PUBLIC_API_KEY=...`
  - `API_SECRET_KEY=...`
  - `CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000`

- Start services:

```bash
docker-compose up --build
```

The frontend proxies `/api/*` requests to `http://backend:8000/api/*` from the server side.

## Tech Stack

- Next.js 14 — React framework
- Tailwind CSS — Styling
- TypeScript — Type safety
- Lucide React — Icons
