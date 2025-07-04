#!/bin/bash
# Build script for Talk macOS app

echo "Building Talk macOS app..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if whisper.cpp is built
if [ ! -f "whisper.cpp/build/bin/whisper-cli" ]; then
    echo "Error: whisper.cpp not built. Please build it first:"
    echo "  cd whisper.cpp"
    echo "  mkdir build && cd build"
    echo "  cmake .."
    echo "  make"
    exit 1
fi

# Check if models exist
if [ ! -f "whisper.cpp/models/ggml-tiny.en.bin" ]; then
    echo "Warning: Models not found. Please download them:"
    echo "  cd whisper.cpp"
    echo "  ./models/download-ggml-model.sh tiny.en"
    echo "  ./models/download-ggml-model.sh base.en"
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Building app bundle..."
python setup.py py2app

if [ $? -eq 0 ]; then
    echo "Build successful!"
    echo "App bundle created at: dist/Talk.app"
    echo ""
    echo "To run the app:"
    echo "  open \"dist/Talk.app\""
    echo ""
    echo "Note: The app will need permissions for:"
    echo "  - Microphone access (for recording)"
    echo "  - Accessibility access (for typing text)"
else
    echo "Build failed!"
    exit 1
fi