#!/bin/bash

# ================================================
# Kaso AI Assistant - Full Project Setup
# ================================================

echo ""
echo "========================================"
echo " Kaso AI Assistant - Full Setup"
echo "========================================"
echo ""

# Setup Backend
echo "[Backend Setup]"
echo "----------------------------------------"
cd backend
if [ -f "setup.sh" ]; then
    chmod +x setup.sh
    ./setup.sh
else
    echo "Error: backend/setup.sh not found!"
fi
cd ..

echo ""
echo "[Frontend Setup]"
echo "----------------------------------------"
cd frontend
if [ -f "setup.sh" ]; then
    chmod +x setup.sh
    ./setup.sh
else
    echo "Error: frontend/setup.sh not found!"
fi
cd ..

echo ""
echo "========================================"
echo " Full Setup Complete!"
echo "========================================"
echo ""
echo "To run the application:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend"
echo "    source venv/bin/activate"
echo "    uvicorn app.main:app --reload"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    cd frontend"
echo "    npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo ""
