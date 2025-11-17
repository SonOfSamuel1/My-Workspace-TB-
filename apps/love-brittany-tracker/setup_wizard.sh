#!/bin/bash

# Setup Wizard for Love Brittany Action Plan Tracker

echo "=================================================="
echo "Love Brittany Action Plan Tracker - Setup Wizard"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Please run: source venv/bin/activate"
    echo ""
    exit 1
fi

echo "✅ Virtual environment: Active"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python version: $PYTHON_VERSION"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    echo "Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "✅ .env file exists"
fi
echo ""

# Check credentials
echo "Checking Google credentials..."
if [ -f credentials/credentials.json ]; then
    echo "✅ credentials.json found"
else
    echo "❌ credentials.json not found"
    echo ""
    echo "Please download OAuth credentials from Google Cloud Console:"
    echo "1. Go to: https://console.cloud.google.com/"
    echo "2. APIs & Services → Credentials"
    echo "3. Create OAuth 2.0 Client ID (Desktop app)"
    echo "4. Download and save as: credentials/credentials.json"
    echo ""
fi
echo ""

# Check configuration values
echo "Checking configuration..."
echo ""

# Check email
EMAIL=$(grep "RELATIONSHIP_REPORT_EMAIL=" .env | cut -d'=' -f2)
if [ -z "$EMAIL" ]; then
    echo "❌ Email address not configured"
    echo ""
    read -p "Enter your email address: " USER_EMAIL

    # Update .env file
    if grep -q "RELATIONSHIP_REPORT_EMAIL=" .env; then
        sed -i '' "s|RELATIONSHIP_REPORT_EMAIL=.*|RELATIONSHIP_REPORT_EMAIL=$USER_EMAIL|" .env
    else
        echo "RELATIONSHIP_REPORT_EMAIL=$USER_EMAIL" >> .env
    fi

    echo "✅ Email configured: $USER_EMAIL"
else
    echo "✅ Email configured: $EMAIL"
fi
echo ""

# Check Google Doc ID
DOC_ID=$(grep "RELATIONSHIP_TRACKING_DOC_ID=" .env | cut -d'=' -f2)
if [ -z "$DOC_ID" ]; then
    echo "❌ Google Doc ID not configured"
    echo ""
    echo "To set up your tracking document:"
    echo "1. Go to: https://docs.google.com/"
    echo "2. Create a new document"
    echo "3. Copy template from: RELATIONSHIP_TRACKING_TEMPLATE.md"
    echo "4. Paste into your new document"
    echo "5. Get the Document ID from URL:"
    echo "   https://docs.google.com/document/d/[DOCUMENT_ID]/edit"
    echo ""
    read -p "Enter your Document ID (or press Enter to skip): " USER_DOC_ID

    if [ ! -z "$USER_DOC_ID" ]; then
        # Update .env file
        if grep -q "RELATIONSHIP_TRACKING_DOC_ID=" .env; then
            sed -i '' "s|RELATIONSHIP_TRACKING_DOC_ID=.*|RELATIONSHIP_TRACKING_DOC_ID=$USER_DOC_ID|" .env
        else
            echo "RELATIONSHIP_TRACKING_DOC_ID=$USER_DOC_ID" >> .env
        fi

        echo "✅ Document ID configured"
    else
        echo "⏭️  Skipped - you can add this later in .env file"
    fi
else
    echo "✅ Google Doc ID configured"
fi
echo ""

# Summary
echo "=================================================="
echo "Setup Summary"
echo "=================================================="
echo ""

# Run validation
echo "Running system validation..."
echo ""
python src/relationship_main.py --validate

echo ""
echo "=================================================="
echo "Next Steps"
echo "=================================================="
echo ""
echo "1. If validation passed, generate a test report:"
echo "   python src/relationship_main.py --generate --no-email"
echo ""
echo "2. Review the HTML report in the output/ folder"
echo ""
echo "3. Send yourself a test email:"
echo "   python src/relationship_main.py --generate"
echo ""
echo "4. Set up automated scheduling:"
echo "   python src/relationship_scheduler.py"
echo ""
echo "📚 Documentation:"
echo "   - QUICK_START_RELATIONSHIP.md"
echo "   - RELATIONSHIP_SETUP_GUIDE.md"
echo ""
echo "Good luck! 💝"
echo ""
