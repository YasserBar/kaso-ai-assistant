# Kaso AI Assistant - Frontend

Web interface for Kaso AI Assistant built with Next.js and Tailwind CSS.

## Features

- 💬 **Chat Interface** - Real-time streaming responses
- 📜 **Conversation History** - Browse and search past conversations
- 🔍 **Search** - Find conversations by keyword
- 📱 **Responsive** - Works on desktop and mobile
- 🌙 **Dark Mode** - Automatic dark mode support
- 🌍 **RTL Support** - Arabic language support

## Setup

### Prerequisites

- Node.js 18+
- Backend server running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Create environment file
# Copy env.example.txt to .env.local and edit:
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_API_KEY=your_api_key_here

# Start development server
npm run dev
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: http://localhost:8000) |
| `NEXT_PUBLIC_API_KEY` | API key for authentication (must match backend) |

## Project Structure

```
src/
├── app/
│   ├── layout.tsx          # Root layout with fonts
│   ├── page.tsx            # Main chat page
│   └── globals.css         # Global styles
├── components/
│   ├── ChatInterface.tsx   # Chat messages + input
│   └── Sidebar.tsx         # Conversation history
└── lib/
    ├── api.ts              # API client with SSE streaming
    ├── config.ts           # Configuration
    └── types.ts            # TypeScript types
```

## API Integration

The frontend connects to the FastAPI backend using:

- **SSE Streaming** - Real-time token-by-token responses
- **REST API** - CRUD operations for conversations
- **X-API-Key Header** - Authentication

## Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

## Tech Stack

- **Next.js 14** - React framework
- **Tailwind CSS** - Styling
- **TypeScript** - Type safety
- **Lucide React** - Icons
