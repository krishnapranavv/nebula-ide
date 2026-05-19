#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Nebula IDE — EC2 Bootstrap Script
# Run once on a fresh Amazon Linux 2023 / Ubuntu 22.04 t3.micro instance
#
# What this does:
#   1. Installs Docker + Docker Compose
#   2. Clones the repository
#   3. Builds sandbox images
#   4. Pulls secrets from AWS SSM Parameter Store
#   5. Starts the application via docker-compose
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR/nebula-ide/main/infrastructure/scripts/ec2-bootstrap.sh | bash
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

LOG="/var/log/nebula-ide-bootstrap.log"
exec > >(tee -a "$LOG") 2>&1

echo "═══════════════════════════════════════"
echo "  Nebula IDE EC2 Bootstrap"
echo "  $(date)"
echo "═══════════════════════════════════════"

# ── Detect OS ─────────────────────────────────────────────────────────────────
if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$ID
else
  OS="unknown"
fi
echo "OS: $OS"

# ── System update + Docker install ────────────────────────────────────────────
echo ""
echo "▶ Installing system dependencies..."

if [[ "$OS" == "ubuntu" ]]; then
  apt-get update -q
  apt-get install -y -q git curl ca-certificates gnupg lsb-release python3-pip

  # Docker
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin

elif [[ "$OS" == "amzn" ]]; then
  yum update -y -q
  yum install -y -q git curl python3-pip
  amazon-linux-extras install docker -y || yum install -y docker
  yum install -y docker-compose-plugin 2>/dev/null || pip3 install docker-compose

fi

systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user 2>/dev/null || usermod -aG docker ubuntu 2>/dev/null || true

echo "  ✓ Docker $(docker --version)"

# ── Clone repository ──────────────────────────────────────────────────────────
echo ""
echo "▶ Cloning repository..."
REPO_URL="${NEBULA_REPO_URL:-https://github.com/YOUR_ORG/nebula-ide.git}"
APP_DIR="/opt/nebula-ide"

if [ -d "$APP_DIR" ]; then
  cd "$APP_DIR" && git pull
  echo "  ✓ Repository updated"
else
  git clone "$REPO_URL" "$APP_DIR"
  echo "  ✓ Repository cloned to $APP_DIR"
fi

cd "$APP_DIR"

# ── Fetch secrets from SSM Parameter Store ────────────────────────────────────
echo ""
echo "▶ Fetching secrets from SSM Parameter Store..."

get_ssm() {
  aws ssm get-parameter --name "$1" --with-decryption --query "Parameter.Value" --output text 2>/dev/null || echo ""
}

SECRET_KEY=$(get_ssm "/nebula-ide/SECRET_KEY")
ANTHROPIC_KEY=$(get_ssm "/nebula-ide/ANTHROPIC_API_KEY")
CLOUDFRONT_URL=$(get_ssm "/nebula-ide/CLOUDFRONT_URL")

# Write .env from SSM values
cat > backend/.env << EOF
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=${SECRET_KEY}
AWS_REGION=us-east-1
S3_BUCKET=nebula-ide-projects
ANTHROPIC_API_KEY=${ANTHROPIC_KEY}
AI_MODEL=claude-haiku-4-5-20251001
ALLOWED_ORIGINS=["${CLOUDFRONT_URL}"]
SANDBOX_TIMEOUT_SECONDS=10
SANDBOX_MEMORY_LIMIT=128m
EOF

echo "  ✓ Secrets loaded from SSM"

# ── Build Docker images ────────────────────────────────────────────────────────
echo ""
echo "▶ Building sandbox Docker images..."
docker build -t nebula-sandbox-python:latest -f infrastructure/docker/sandbox/Dockerfile.python .
docker build -t nebula-sandbox-node:latest   -f infrastructure/docker/sandbox/Dockerfile.node .
docker build -t nebula-sandbox-cpp:latest    -f infrastructure/docker/sandbox/Dockerfile.cpp .
echo "  ✓ Sandbox images built"

# ── Start application ─────────────────────────────────────────────────────────
echo ""
echo "▶ Starting Nebula IDE..."
docker compose -f docker-compose.yml up -d --build
echo "  ✓ Application started"

# ── Nginx + HTTPS ─────────────────────────────────────────────────────────────
echo ""
echo "▶ Configuring Nginx + Let's Encrypt..."
if [[ "$OS" == "ubuntu" ]]; then
  apt-get install -y -q nginx certbot python3-certbot-nginx
  cp infrastructure/nginx/nebula-ide.conf /etc/nginx/sites-available/nebula-ide.conf
  ln -sf /etc/nginx/sites-available/nebula-ide.conf /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  echo "  ✓ Nginx configured (run certbot manually to enable HTTPS)"
fi

echo ""
echo "═══════════════════════════════════════"
echo "  Bootstrap complete! ✓"
echo "  API:     http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000/api/health"
echo "  Logs:    docker compose logs -f"
echo "═══════════════════════════════════════"