#!/bin/bash

# Django Backend Setup Script
echo "🚀 Setting up Django Backend for AccountEezy"

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: This script must be run from the Django backend directory"
    echo "   Expected: /Users/gregorygrant/Desktop/Websites/Python/React Django Webapp/account_easy/django_backend"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing Python packages..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔧 Creating .env file..."
    cat > .env << EOL
SECRET_KEY=django-insecure-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
EOL
fi

# Run migrations
echo "🗄️  Creating database tables..."
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
echo "👤 Creating Django superuser (optional)..."
echo "You can skip this by pressing Ctrl+C"
python manage.py createsuperuser --email admin@accounteezy.com || echo "Skipped superuser creation"

echo "✅ Django backend setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Start the Django server: python manage.py runserver"
echo "2. Update your React client to use: http://localhost:8000/api"
echo "3. Test the API endpoints"
echo ""
echo "📋 Available API endpoints:"
echo "   - POST /api/auth/register/"
echo "   - POST /api/auth/login/"
echo "   - GET  /api/auth/profile/"
echo "   - GET  /api/auth/health/"