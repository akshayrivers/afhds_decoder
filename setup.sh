#!/bin/bash
# Passive RF Analysis Setup Script (macOS)
# Tested on macOS Ventura / Sonoma (Intel + Apple Silicon)

set -e

echo "========================================="
echo "Passive RF Analysis - macOS Setup"
echo "========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}This script is for macOS only.${NC}"
    exit 1
fi

# Check Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Homebrew not found.${NC}"
    echo "Install it from: https://brew.sh"
    exit 1
fi

echo ""
echo -e "${YELLOW}[2/6] Installing HackRF tools...${NC}"
brew install hackrf

echo ""
echo -e "${YELLOW}[3/6] Installing GNU Radio and SDR drivers...${NC}"
brew install gnuradio
brew install gr-osmosdr

echo ""
echo -e "${YELLOW}[4/6] Installing Python environment...${NC}"
brew install python

python3 -m pip install --user --upgrade pip
python3 -m pip install --user \
    numpy \
    scipy \
    matplotlib \
    pyyaml

echo ""
echo -e "${YELLOW}[5/6] Verifying installations...${NC}"

# Test HackRF
if command -v hackrf_info &> /dev/null; then
    echo -e "${GREEN}✓ HackRF tools installed${NC}"
else
    echo -e "${RED}✗ HackRF tools not found${NC}"
fi

# Test GNU Radio
if python3 -c "import gnuradio" 2>/dev/null; then
    echo -e "${GREEN}✓ GNU Radio Python bindings OK${NC}"
else
    echo -e "${RED}✗ GNU Radio Python bindings failed${NC}"
fi

# Test osmosdr
if python3 -c "import osmosdr" 2>/dev/null; then
    echo -e "${GREEN}✓ gr-osmosdr OK${NC}"
else
    echo -e "${RED}✗ gr-osmosdr import failed${NC}"
fi

# Test Python libs
if python3 -c "import numpy, scipy, matplotlib" 2>/dev/null; then
    echo -e "${GREEN}✓ Python scientific stack OK${NC}"
else
    echo -e "${RED}✗ Python packages missing${NC}"
fi

echo ""
echo -e "${YELLOW}[6/6] Creating project directories...${NC}"
mkdir -p captures
mkdir -p logs
mkdir -p analysis

echo ""
echo "========================================="
echo -e "${GREEN}macOS setup complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Plug in HackRF"
echo "  2. Run: hackrf_info"
echo "  3. Launch GNU Radio: gnuradio-companion"
echo ""
echo -e "${YELLOW}Note:${NC} macOS does not require udev rules or group changes."
echo ""
