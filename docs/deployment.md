# News Llama Production Deployment Guide

This guide covers deploying News Llama web application to a production Linux server with systemd, nginx, automated backups, and monitoring.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Setup](#system-setup)
3. [Application Installation](#application-installation)
4. [Database Setup](#database-setup)
5. [Systemd Service](#systemd-service)
6. [Nginx Reverse Proxy](#nginx-reverse-proxy)
7. [SSL/TLS Configuration](#ssltls-configuration)
8. [Database Backups](#database-backups)
9. [Log Rotation](#log-rotation)
10. [Monitoring](#monitoring)
11. [Security Hardening](#security-hardening)
12. [Maintenance](#maintenance)

## Prerequisites

- **OS**: Ubuntu 22.04 LTS or similar (Debian-based)
- **Python**: 3.10 or higher
- **RAM**: 2GB minimum (4GB recommended for LLM integration)
- **Disk**: 10GB minimum (20GB+ recommended for logs and backups)
- **Domain**: Optional but recommended for SSL/TLS

## System Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Dependencies

```bash
# Python and build tools
sudo apt install -y python3.10 python3.10-venv python3-pip

# Nginx web server
sudo apt install -y nginx

# SQLite tools (optional, for manual DB inspection)
sudo apt install -y sqlite3

# Certbot for SSL (if using Let's Encrypt)
sudo apt install -y certbot python3-certbot-nginx
```

### 3. Create Service User

```bash
# Create dedicated user for security (no shell access)
sudo useradd -r -s /bin/false -m -d /opt/news-llama newsllama
```

## Application Installation

### 1. Clone Repository

```bash
# Switch to service user
sudo -u newsllama bash

# Clone to service user's home
cd /opt/news-llama
git clone https://github.com/yourusername/news-llama.git .
```

### 2. Setup Virtual Environment

```bash
# Still as newsllama user
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy and edit configuration
cp .env.example .env
nano .env
```

Production `.env` configuration:

```bash
# LLM Configuration (point to your LLM server)
LLM_API_URL=http://localhost:8000/v1
LLM_MODEL=llama-3.1-8b-instruct
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000

# Database (use absolute path)
DATABASE_URL=sqlite:////opt/news-llama/news_llama.db

# Scheduler (daily generation at 6 AM)
SCHEDULER_ENABLED=true
SCHEDULER_HOUR=6
SCHEDULER_MINUTE=0
SCHEDULER_TIMEZONE=America/Los_Angeles

# Output directory (ensure writable)
OUTPUT_DIRECTORY=/opt/news-llama/output

# Social Media (optional)
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Processing settings
MAX_ARTICLES_PER_CATEGORY=10
ENABLE_SENTIMENT_ANALYSIS=true
ENABLE_LLM_SOURCE_DISCOVERY=true

# Web server (bind to localhost, nginx will proxy)
HOST=127.0.0.1
PORT=8001

# Testing (disable in production)
TESTING=false
```

### 4. Set Permissions

```bash
# Exit newsllama user shell
exit

# Set ownership
sudo chown -R newsllama:newsllama /opt/news-llama

# Set permissions (secure)
sudo chmod 700 /opt/news-llama
sudo chmod 600 /opt/news-llama/.env
sudo chmod 755 /opt/news-llama/output
```

## Database Setup

### 1. Run Migrations

```bash
sudo -u newsllama bash -c "cd /opt/news-llama && source venv/bin/activate && alembic upgrade head"
```

### 2. Verify Database

```bash
# Check database file created
sudo -u newsllama ls -lh /opt/news-llama/news_llama.db

# Verify schema
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db ".schema"
```

### 3. Enable WAL Mode (Performance)

```bash
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "PRAGMA journal_mode=WAL;"
```

## Systemd Service

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/news-llama.service
```

Service configuration:

```ini
[Unit]
Description=News Llama Web Application
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=newsllama
Group=newsllama
WorkingDirectory=/opt/news-llama
Environment="PATH=/opt/news-llama/venv/bin"
ExecStart=/opt/news-llama/venv/bin/uvicorn src.web.app:app --host 127.0.0.1 --port 8001 --workers 2

# Restart policy
Restart=always
RestartSec=10

# Logging
StandardOutput=append:/var/log/news-llama/access.log
StandardError=append:/var/log/news-llama/error.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/news-llama/output /opt/news-llama/news_llama.db /opt/news-llama/news_llama.db-shm /opt/news-llama/news_llama.db-wal

# Resource limits
LimitNOFILE=4096
MemoryMax=2G

[Install]
WantedBy=multi-user.target
```

### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/news-llama
sudo chown newsllama:newsllama /var/log/news-llama
sudo chmod 755 /var/log/news-llama
```

### 3. Enable and Start Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable news-llama

# Start service
sudo systemctl start news-llama

# Check status
sudo systemctl status news-llama
```

### 4. Verify Service

```bash
# Check if listening on port 8001
ss -tlnp | grep 8001

# Check logs
sudo journalctl -u news-llama -f

# Test health endpoint
curl http://127.0.0.1:8001/health/scheduler
```

## Nginx Reverse Proxy

### 1. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/news-llama
```

Nginx configuration:

```nginx
# HTTP configuration (will redirect to HTTPS after SSL setup)
server {
    listen 80;
    listen [::]:80;
    server_name news-llama.example.com;  # Replace with your domain

    # Redirect to HTTPS (uncomment after SSL setup)
    # return 301 https://$server_name$request_uri;

    # Proxy to application
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running newsletter generation
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Static files (optional, if serving newsletters directly)
    location /output/ {
        alias /opt/news-llama/output/;
        autoindex off;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint (no auth required)
    location /health/ {
        proxy_pass http://127.0.0.1:8001;
        access_log off;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client body size (for potential file uploads)
    client_max_body_size 10M;

    # Logging
    access_log /var/log/nginx/news-llama-access.log;
    error_log /var/log/nginx/news-llama-error.log;
}
```

### 2. Enable Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/news-llama /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 3. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Check firewall status
sudo ufw status
```

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

```bash
# Obtain certificate (interactive)
sudo certbot --nginx -d news-llama.example.com

# Certificate auto-renewal test
sudo certbot renew --dry-run
```

Certbot will automatically:
- Obtain SSL certificate
- Update nginx configuration
- Enable HTTPS redirect
- Setup auto-renewal cron job

### Manual SSL Configuration

If using custom certificates:

```bash
sudo nano /etc/nginx/sites-available/news-llama
```

Add HTTPS server block:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name news-llama.example.com;

    # SSL certificates
    ssl_certificate /etc/ssl/certs/news-llama.crt;
    ssl_certificate_key /etc/ssl/private/news-llama.key;

    # SSL configuration (modern, secure)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # ... rest of configuration from HTTP block ...
}
```

## Database Backups

### 1. Create Backup Script

```bash
sudo nano /opt/news-llama/backup.sh
```

Backup script:

```bash
#!/bin/bash
set -euo pipefail

# Configuration
DB_PATH="/opt/news-llama/news_llama.db"
BACKUP_DIR="/opt/news-llama/backups"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Timestamp for backup file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/news_llama_${TIMESTAMP}.db"

# Perform backup (SQLite online backup)
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Compress backup
gzip "$BACKUP_FILE"

# Delete old backups (keep last N days)
find "$BACKUP_DIR" -name "news_llama_*.db.gz" -mtime +$RETENTION_DAYS -delete

# Log success
echo "$(date): Backup completed: ${BACKUP_FILE}.gz" >> /var/log/news-llama/backup.log

# Optional: Upload to S3/Backblaze/etc.
# aws s3 cp "${BACKUP_FILE}.gz" s3://your-bucket/backups/
```

### 2. Set Permissions

```bash
sudo chown newsllama:newsllama /opt/news-llama/backup.sh
sudo chmod 750 /opt/news-llama/backup.sh
```

### 3. Schedule with Cron

```bash
sudo crontab -u newsllama -e
```

Add daily backup at 3 AM:

```cron
# Daily database backup at 3 AM
0 3 * * * /opt/news-llama/backup.sh

# Weekly cleanup of old output files (optional)
0 4 * * 0 find /opt/news-llama/output -name "news-*.html" -mtime +90 -delete
```

### 4. Test Backup

```bash
sudo -u newsllama /opt/news-llama/backup.sh
ls -lh /opt/news-llama/backups/
```

### 5. Restore from Backup

```bash
# Stop service
sudo systemctl stop news-llama

# Restore database
cd /opt/news-llama
gunzip -c backups/news_llama_YYYYMMDD_HHMMSS.db.gz > news_llama.db
chown newsllama:newsllama news_llama.db

# Start service
sudo systemctl start news-llama
```

## Log Rotation

### 1. Create Logrotate Configuration

```bash
sudo nano /etc/logrotate.d/news-llama
```

Logrotate configuration:

```
/var/log/news-llama/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0644 newsllama newsllama
    sharedscripts
    postrotate
        systemctl reload news-llama >/dev/null 2>&1 || true
    endscript
}
```

### 2. Test Logrotate

```bash
sudo logrotate -d /etc/logrotate.d/news-llama
sudo logrotate -f /etc/logrotate.d/news-llama
```

## Monitoring

### 1. Health Check Script

```bash
sudo nano /opt/news-llama/healthcheck.sh
```

Health check script:

```bash
#!/bin/bash
set -euo pipefail

# Configuration
HEALTH_URL="http://127.0.0.1:8001/health/scheduler"
LOG_FILE="/var/log/news-llama/healthcheck.log"

# Perform health check
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "$(date): Health check passed (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    exit 0
else
    echo "$(date): Health check FAILED (HTTP $HTTP_CODE)" >> "$LOG_FILE"
    # Optional: Send alert (email, Slack, etc.)
    # echo "News Llama health check failed" | mail -s "Alert: News Llama Down" admin@example.com
    exit 1
fi
```

### 2. Schedule Health Checks

```bash
sudo crontab -e
```

Add health check every 5 minutes:

```cron
*/5 * * * * /opt/news-llama/healthcheck.sh
```

### 3. Monitoring Endpoints

- **Scheduler Status**: `GET /health/scheduler`
  - Returns: `{"running": true, "jobs": [...], "job_count": N}`

- **Generation Metrics**: `GET /health/generation`
  - Returns: `{"total": N, "successful": N, "failed": N, "success_rate": 0.XX, "avg_duration_seconds": XX}`

### 4. External Monitoring (Optional)

Consider integrating with:
- **UptimeRobot**: Free HTTP monitoring
- **Prometheus + Grafana**: Metrics and dashboards
- **Sentry**: Error tracking and alerting

## Security Hardening

### 1. Firewall Configuration

```bash
# Enable firewall
sudo ufw enable

# Allow SSH (adjust port if needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (nginx)
sudo ufw allow 'Nginx Full'

# Deny all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check status
sudo ufw status verbose
```

### 2. Fail2Ban (Optional)

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Create nginx jail
sudo nano /etc/fail2ban/jail.d/nginx.conf
```

Fail2Ban configuration:

```ini
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/news-llama-error.log
maxretry = 5
bantime = 3600

[nginx-noscript]
enabled = true
port = http,https
filter = nginx-noscript
logpath = /var/log/nginx/news-llama-access.log
maxretry = 6
bantime = 3600
```

### 3. Secure Environment File

```bash
# Ensure .env is not world-readable
sudo chmod 600 /opt/news-llama/.env
sudo chown newsllama:newsllama /opt/news-llama/.env

# Verify permissions
ls -l /opt/news-llama/.env
```

### 4. Regular Updates

```bash
# System updates (weekly)
sudo apt update && sudo apt upgrade -y

# Python dependencies (monthly, test in staging first)
sudo -u newsllama bash -c "cd /opt/news-llama && source venv/bin/activate && pip install --upgrade -r requirements.txt"

# Restart service after updates
sudo systemctl restart news-llama
```

### 5. Rate Limiting (Application-Level)

Already implemented in News Llama:
- 10 requests per 60 seconds per user for newsletter generation
- Configurable in `src/web/rate_limiter.py`

### 6. Database Encryption (Optional)

For sensitive deployments, consider using SQLCipher:

```bash
pip install sqlcipher3-binary
```

Update `DATABASE_URL` in `.env`:
```bash
DATABASE_URL=sqlite+pysqlcipher:///path/to/encrypted.db?cipher=aes-256-cfb&kdf_iter=64000
```

## Maintenance

### Common Operations

#### View Service Logs

```bash
# Real-time logs
sudo journalctl -u news-llama -f

# Last 100 lines
sudo journalctl -u news-llama -n 100

# Logs since yesterday
sudo journalctl -u news-llama --since yesterday
```

#### Restart Service

```bash
sudo systemctl restart news-llama
```

#### Update Application

```bash
# Pull latest code
sudo -u newsllama bash -c "cd /opt/news-llama && git pull"

# Update dependencies
sudo -u newsllama bash -c "cd /opt/news-llama && source venv/bin/activate && pip install -r requirements.txt"

# Run migrations
sudo -u newsllama bash -c "cd /opt/news-llama && source venv/bin/activate && alembic upgrade head"

# Restart service
sudo systemctl restart news-llama
```

#### Database Maintenance

```bash
# Vacuum database (reclaim space)
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "VACUUM;"

# Analyze database (update statistics)
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "ANALYZE;"

# Check integrity
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "PRAGMA integrity_check;"
```

#### Clean Old Files

```bash
# Remove old newsletters (older than 90 days)
find /opt/news-llama/output -name "news-*.html" -mtime +90 -delete

# Remove old logs (handled by logrotate, but manual if needed)
find /var/log/news-llama -name "*.log.*" -mtime +30 -delete
```

### Troubleshooting

#### Service Won't Start

```bash
# Check service status
sudo systemctl status news-llama

# Check logs
sudo journalctl -u news-llama -n 50

# Common issues:
# - Port 8001 already in use: Change PORT in .env
# - Database locked: Stop service, check for stale processes
# - Permission denied: Verify file ownership and permissions
```

#### High Memory Usage

```bash
# Check memory usage
sudo systemctl status news-llama | grep Memory

# Adjust memory limit in service file
sudo nano /etc/systemd/system/news-llama.service
# Change: MemoryMax=2G (increase if needed)

sudo systemctl daemon-reload
sudo systemctl restart news-llama
```

#### Slow Newsletter Generation

```bash
# Check generation metrics
curl http://127.0.0.1:8001/health/generation

# Common causes:
# - LLM server slow/unresponsive: Check LLM_API_URL in .env
# - Network issues: Test connectivity to Reddit/Twitter APIs
# - Large number of sources: Adjust MAX_ARTICLES_PER_CATEGORY in .env
```

#### Database Corruption

```bash
# Stop service
sudo systemctl stop news-llama

# Backup current database
sudo -u newsllama cp /opt/news-llama/news_llama.db /opt/news-llama/news_llama.db.corrupt

# Restore from latest backup
sudo -u newsllama gunzip -c /opt/news-llama/backups/news_llama_*.db.gz > /opt/news-llama/news_llama.db

# Start service
sudo systemctl start news-llama
```

### Performance Tuning

#### Uvicorn Workers

Adjust workers in systemd service file:

```ini
# For CPU-bound workloads: workers = (2 x CPU cores) + 1
# For I/O-bound workloads (News Llama): workers = 2-4
ExecStart=/opt/news-llama/venv/bin/uvicorn src.web.app:app --host 127.0.0.1 --port 8001 --workers 2
```

#### SQLite Performance

```bash
# Enable WAL mode (better concurrency)
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "PRAGMA journal_mode=WAL;"

# Set cache size (in KB, default 2MB, increase for better performance)
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "PRAGMA cache_size=-10000;"  # 10MB

# Set synchronous mode (2 = FULL for safety, 1 = NORMAL for speed)
sudo -u newsllama sqlite3 /opt/news-llama/news_llama.db "PRAGMA synchronous=NORMAL;"
```

#### Nginx Caching

Add to nginx configuration:

```nginx
# Cache static files
location /static/ {
    alias /opt/news-llama/src/web/static/;
    expires 7d;
    add_header Cache-Control "public, immutable";
}

# Cache newsletters (only for completed status)
location ~ ^/newsletters/([a-z0-9-]+)$ {
    proxy_pass http://127.0.0.1:8001;
    proxy_cache_valid 200 1h;
    add_header X-Cache-Status $upstream_cache_status;
}
```

---

## Summary Checklist

- [ ] System dependencies installed (Python, nginx, certbot)
- [ ] Service user created (`newsllama`)
- [ ] Application installed to `/opt/news-llama`
- [ ] Virtual environment created and dependencies installed
- [ ] `.env` configured with production settings
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Systemd service created and enabled
- [ ] Nginx reverse proxy configured
- [ ] SSL/TLS certificate obtained and configured
- [ ] Firewall configured (UFW)
- [ ] Database backup script created and scheduled (cron)
- [ ] Log rotation configured (logrotate)
- [ ] Health check monitoring setup
- [ ] Service tested and verified running

## Additional Resources

- [News Llama README](../README.md) - Application overview
- [User Guide](user-guide.md) - End-user documentation
- [Architecture Documentation](architecture.md) - Technical details
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/) - Official docs
- [Nginx Documentation](https://nginx.org/en/docs/) - Nginx reference
- [Let's Encrypt](https://letsencrypt.org/) - Free SSL certificates

## Support

For issues or questions:
- GitHub Issues: [yourusername/news-llama/issues](https://github.com/yourusername/news-llama/issues)
- Documentation: [docs/](../)
