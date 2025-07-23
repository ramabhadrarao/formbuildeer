# 
# FILE: deploy.sh
# PURPOSE: Production deployment script
#

#!/bin/bash
set -e

echo "🚀 Starting Dynamic Forms deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    print_status "Environment variables loaded from .env"
else
    print_warning ".env file not found. Please create one based on .env.example"
fi

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_error "Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

print_status "Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Check if MySQL is available
print_status "Checking MySQL connection..."
if ! mysql -h"${DB_HOST:-localhost}" -u"${DB_USER:-root}" -p"${DB_PASSWORD}" -e "SELECT 1;" &> /dev/null; then
    print_error "Cannot connect to MySQL. Please check your database configuration."
    exit 1
fi

print_status "MySQL connection successful"

# Create database if it doesn't exist
print_status "Creating database if not exists..."
mysql -h"${DB_HOST:-localhost}" -u"${DB_USER:-root}" -p"${DB_PASSWORD}" -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME:-dynamic_forms_db} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Run migrations
print_status "Running database migrations..."
python manage.py migrate

# Collect static files
print_status "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser and sample data
print_status "Setting up initial data..."
python manage.py create_superuser

# Check if Redis is available (for Celery)
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_status "Redis is available. Starting Celery workers..."
        
        # Kill existing Celery processes
        pkill -f "celery worker" || true
        pkill -f "celery beat" || true
        
        # Start Celery worker in background
        nohup celery -A dynamic_forms_project worker --loglevel=info &
        
        # Start Celery beat scheduler in background
        nohup celery -A dynamic_forms_project beat --loglevel=info &
        
        print_status "Celery workers started"
    else
        print_warning "Redis is not running. Celery features will not be available."
    fi
else
    print_warning "Redis is not installed. Celery features will not be available."
fi

# Create systemd service files for production
create_systemd_services() {
    if [ "$EUID" -ne 0 ]; then
        print_warning "Skipping systemd service creation (requires root privileges)"
        return
    fi
    
    PROJECT_DIR=$(pwd)
    USER=$(whoami)
    
    # Gunicorn service
    cat > /etc/systemd/system/dynamic-forms-gunicorn.service << EOF
[Unit]
Description=Dynamic Forms Gunicorn daemon
Requires=dynamic-forms-gunicorn.socket
After=network.target

[Service]
Type=notify
User=$USER
Group=www-data
RuntimeDirectory=gunicorn
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/run/gunicorn/dynamic-forms.sock dynamic_forms_project.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=30
KillMode=mixed
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

    # Gunicorn socket
    cat > /etc/systemd/system/dynamic-forms-gunicorn.socket << EOF
[Unit]
Description=Dynamic Forms Gunicorn socket

[Socket]
ListenStream=/run/gunicorn/dynamic-forms.sock
SocketUser=www-data

[Install]
WantedBy=sockets.target
EOF

    # Celery worker service
    cat > /etc/systemd/system/dynamic-forms-celery.service << EOF
[Unit]
Description=Dynamic Forms Celery Worker
After=network.target

[Service]
Type=forking
User=$USER
Group=$USER
EnvironmentFile=$PROJECT_DIR/.env
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/celery multi start worker1 -A dynamic_forms_project --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO
ExecStop=$PROJECT_DIR/venv/bin/celery multi stopwait worker1 --pidfile=/var/run/celery/%n.pid
ExecReload=$PROJECT_DIR/venv/bin/celery multi restart worker1 -A dynamic_forms_project --pidfile=/var/run/celery/%n.pid --logfile=/var/log/celery/%n%I.log --loglevel=INFO
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    # Celery beat service
    cat > /etc/systemd/system/dynamic-forms-celerybeat.service << EOF
[Unit]
Description=Dynamic Forms Celery Beat
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
EnvironmentFile=$PROJECT_DIR/.env
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/celery -A dynamic_forms_project beat --loglevel=INFO
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    # Create necessary directories
    mkdir -p /var/run/celery /var/log/celery
    chown $USER:$USER /var/run/celery /var/log/celery

    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable dynamic-forms-gunicorn.socket
    systemctl enable dynamic-forms-celery.service
    systemctl enable dynamic-forms-celerybeat.service
    
    print_status "Systemd services created and enabled"
}

# Create Nginx configuration
create_nginx_config() {
    if [ "$EUID" -ne 0 ]; then
        print_warning "Skipping Nginx configuration (requires root privileges)"
        return
    fi
    
    DOMAIN=${DOMAIN:-localhost}
    PROJECT_DIR=$(pwd)
    
    cat > /etc/nginx/sites-available/dynamic-forms << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    client_max_body_size 100M;
    
    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        root $PROJECT_DIR;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        root $PROJECT_DIR;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn/dynamic-forms.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Enable the site
    ln -sf /etc/nginx/sites-available/dynamic-forms /etc/nginx/sites-enabled/
    
    # Test Nginx configuration
    nginx -t && systemctl reload nginx
    
    print_status "Nginx configuration created and enabled"
}

# Run tests
print_status "Running tests..."
if python manage.py test --verbosity=2; then
    print_status "All tests passed!"
else
    print_error "Some tests failed. Please review and fix before deploying to production."
    exit 1
fi

# Security check
print_status "Running security checks..."
python manage.py check --deploy

# Display deployment information
print_status "
╔══════════════════════════════════════════════════╗
║              DEPLOYMENT COMPLETE!                ║
╚══════════════════════════════════════════════════╝

🌟 Dynamic Forms has been successfully deployed!

📋 Quick Start:
   • Development server: python manage.py runserver
   • Admin panel: http://localhost:8000/admin/
   • Default credentials: admin / admin123

📚 Documentation:
   • API docs: http://localhost:8000/api/
   • User guide: Check the README.md

🔧 Production Setup:
   • Run as root to create systemd services and Nginx config
   • Configure SSL/TLS certificates
   • Set up proper backup procedures
   • Monitor logs in /var/log/

🚀 Additional Commands:
   • Create forms: Use the admin panel
   • Manage users: python manage.py shell
   • View logs: tail -f /var/log/dynamic-forms/

Happy form building! 🎉
"

# Cleanup
deactivate 2>/dev/null || true

exit 0