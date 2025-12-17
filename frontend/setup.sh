#!/bin/bash
# ================================================
# Kaso AI Assistant - Frontend Setup Script
# ================================================

echo ""
echo "========================================"
echo " Kaso AI Assistant - Frontend Setup"
echo "========================================"
echo ""

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org"
    exit 1
fi

# Install dependencies
echo "[1/3] Installing dependencies..."
npm install
echo "      Dependencies installed."

# Create .env.local if not exists
echo "[2/3] Setting up environment..."
if [ ! -f ".env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
    echo "NEXT_PUBLIC_API_KEY=change-me-in-production" >> .env.local
    echo "      Created .env.local file."
    echo ""
    echo "[IMPORTANT] Please edit .env.local:"
    echo "  - NEXT_PUBLIC_API_KEY: Must match backend API_SECRET_KEY"
    echo ""
else
    echo "      .env.local file already exists."
fi

# Build check
echo "[3/3] Checking build..."
npm run lint || echo "[WARNING] Lint errors found."

echo ""
echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Make sure backend is running at http://localhost:8000"
echo "  2. Edit .env.local with your API key"
echo "  3. Run: npm run dev"
echo "  4. Open: http://localhost:3000"
echo ""
