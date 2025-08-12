#!/bin/bash

# E-Paper Image Frame Installation Script for Raspberry Pi
# This script sets up a Python virtual environment and installs all dependencies

set -e  # Exit on any error

echo "🖼️  E-Paper Image Frame Installation Script"
echo "=============================================="
echo "🍓 Designed for Raspberry Pi running Raspbian/Raspberry Pi OS"
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    echo "   Please install Python 3.8 or newer and try again"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)" 2>/dev/null; then
    echo "❌ Error: Python $PYTHON_VERSION detected, but Python $REQUIRED_VERSION or newer is required"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"

# Check if we're already in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "⚠️  Warning: Already in a virtual environment: $VIRTUAL_ENV"
    echo "   This script will install packages in the current environment"
    echo
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled"
        exit 1
    fi
    VENV_PATH="$VIRTUAL_ENV"
    SKIP_VENV=true
else
    SKIP_VENV=false
    VENV_PATH="$(pwd)/venv"
fi

# Create virtual environment if not skipping
if [[ "$SKIP_VENV" == "false" ]]; then
    echo "📦 Creating Python virtual environment..."
    if [[ -d "venv" ]]; then
        echo "   Virtual environment already exists at ./venv"
        read -p "   Remove existing environment and create new one? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "   Removing existing virtual environment..."
            rm -rf venv
        else
            echo "   Using existing virtual environment"
        fi
    fi
    
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        echo "   ✅ Virtual environment created"
    fi
    
    # Activate virtual environment
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
    echo "   ✅ Virtual environment activated"
else
    echo "🔧 Using current virtual environment..."
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip
echo "   ✅ pip upgraded"

# Install requirements
echo "📚 Installing Python dependencies..."
if [[ ! -f "requirements.txt" ]]; then
    echo "❌ Error: requirements.txt not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

echo "   Installing packages from requirements.txt..."
pip install -r requirements.txt
echo "   ✅ All dependencies installed"

# Create .env file if it doesn't exist
echo "⚙️  Setting up environment configuration..."
if [[ ! -f ".env" ]]; then
    echo "   Creating .env file..."
    cat > .env << 'EOF'
ENVIRONMENT=development
EOF
    echo "   ✅ .env file created with development settings"
else
    echo "   ✅ .env file already exists"
fi

# Initialize database
echo "🗄️  Setting up database..."
if [[ -f "migrate_db.py" ]]; then
    python migrate_db.py
    echo "   ✅ Database initialized"
else
    echo "   ⚠️  migrate_db.py not found, skipping database setup"
fi

# Run additional migrations if they exist
if [[ -f "migrate_aspect_ratio.py" ]]; then
    echo "   Running additional migrations..."
    python migrate_aspect_ratio.py
    echo "   ✅ Migrations completed"
fi

# Create necessary directories
echo "📁 Creating required directories..."
python -c "
import os
from pathlib import Path

# Create directories
dirs = ['static/uploads', 'static/thumbs', 'static/css']
for dir_path in dirs:
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    print(f'   ✅ {dir_path}')
"

echo
echo "🎉 Installation completed successfully!"
echo
echo "📋 Next steps:"
if [[ "$SKIP_VENV" == "false" ]]; then
    echo "   1. Activate the virtual environment:"
    echo "      source venv/bin/activate"
    echo
fi
echo "   2. Start the application:"
echo "      python app.py"
echo
echo "   3. Open your browser to:"
echo "      http://localhost:8080"
echo "      or http://[raspberry-pi-ip]:8080 from another device"
echo
echo "💡 Tips:"
echo "   • Upload images through the web interface"
echo "   • Use the crop tool to frame your photos perfectly"
echo "   • Enable slideshow mode for automatic rotation"
echo "   • Check README.md for detailed usage instructions"
echo "   • Connect your Pimoroni Inky display for real e-ink output"
echo
echo "🐛 Development mode is enabled by default"
echo "   The app will simulate the e-ink display in the console"
echo "   Change ENVIRONMENT=production in .env for real hardware"
echo "   Make sure your Inky display is properly connected first!"
echo

# Show activation command for easy copy-paste
if [[ "$SKIP_VENV" == "false" ]]; then
    echo "🚀 Quick start command:"
    echo "   source venv/bin/activate && python app.py"
    echo
fi
