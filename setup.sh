#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# Carrigtwohill Historical Research Repository – Setup
# Run once:  bash setup.sh
# ─────────────────────────────────────────────────────────
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🏰 Carrigtwohill Historical Research Repository"
echo "  Setup Script"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✓ Python $(python3 --version)"

# Install dependencies
echo ""
echo "Installing Python dependencies …"
pip3 install -r requirements.txt --quiet

echo "✓ Dependencies installed"

# Create data directories
mkdir -p data/archives
echo "✓ Data directories created"

# Initialise database
python3 -c "import db; db.init_db()"
echo "✓ Database initialised"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Setup complete! To start the system:"
echo ""
echo "  Run collector only:    python3 run.py collect"
echo "  Start web interface:   python3 run.py web"
echo "  Collect then browse:   python3 run.py both"
echo ""
echo "  Then open: http://localhost:5050"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
