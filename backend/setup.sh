#!/bin/bash
# ================================================
# Kaso AI Assistant - Backend Setup Script
# ================================================

echo ""
echo "========================================"
echo " Kaso AI Assistant - Backend Setup"
echo "========================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed"
    echo "Please install Python 3.10+ from https://python.org"
    exit 1
fi

# Create virtual environment
echo "[1/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "      Virtual environment created."
else
    echo "      Virtual environment already exists."
fi

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "[3/5] Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "[4/5] Installing dependencies..."
pip install -r requirements.txt -q
pip install -r requirements-test.txt -q
echo "      Dependencies installed."

# Create .env if not exists
echo "[5/5] Setting up environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "      Created .env file from template."
    echo ""
    echo "[IMPORTANT] Please edit .env and add your API keys:"
    echo "  - GROQ_API_KEY: Get from https://console.groq.com/"
    echo "  - API_SECRET_KEY: Generate a random key"
    echo ""
else
    echo "      .env file already exists."
fi

# Create data directories
mkdir -p data/raw data/processed data/chunks

echo ""
echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your API keys"
echo "  2. Run: python -m data_pipeline.run_pipeline --markdown '../kaso_research_report.md'"
echo "  3. Start server: uvicorn app.main:app --reload"
echo ""
