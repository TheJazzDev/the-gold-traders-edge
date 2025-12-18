#!/bin/bash

# Gold Trader's Edge API Startup Script
# For macOS

set -e

echo "========================================"
echo "🚀 Starting Gold Trader's Edge API"
echo "========================================"

# Check if .env exists, if not copy from example
if [ ! -f .env ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please update with your settings."
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if requirements are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
fi

# Check if data exists
if [ ! -d "data/processed" ] || [ -z "$(ls -A data/processed)" ]; then
    echo "⚠️  No data found. Fetching XAUUSD data..."
    python3 fetch_real_data.py --years 2 --timeframe 4h --clean
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting API server..."
echo "   - API: http://localhost:8000"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/health"
echo ""
echo "Press CTRL+C to stop the server"
echo "========================================"
echo ""

# Start the API server
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
