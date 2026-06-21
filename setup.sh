#!/bin/bash

# BrainDump NextGen - Setup Script

echo "🚀 Setting up BrainDump NextGen..."

# Check Python version
echo "📋 Checking Python version..."
python3 --version

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy example environment file if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file from example..."
    cp .env.example .env
fi

echo "✅ Setup complete!"
echo ""
echo "To get started:"
echo "  source venv/bin/activate"
echo "  make dev"
echo ""
echo "Or run tests:"
echo "  make test"