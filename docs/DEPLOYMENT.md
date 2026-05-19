# Nebula IDE — Deployment Guide

## Architecture overview

```
Browser → CloudFront CDN → S3 (React SPA)
                       ↓
               EC2 t3.micro (FastAPI + Docker)
                       ↓
              DynamoDB  |  S3 (project files)
```

**Estimated monthly cost: ~$11–15** on a $200 student credit budget (~15 months runway).

---

## Prerequisites

- AWS account with student/free credits
- AWS CLI installed and configured
- Docker + Docker Compose (local)
- Node 20+, Python 3.11+

---

## Phase 1 — Local development (free, no AWS needed)

### 1. Clone and install

```bash
git clone https://github.com/YOUR_ORG/nebula-ide.git
cd nebula-ide
make install
```

### 2. Configure environment

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set ANTHROPIC_API_KEY
```

Get a free Anthropic API key at https://console.anthropic.com (includes $5 free credit).

### 3. Start local AWS services

```bash
make dev-deps    # starts DynamoDB Local + LocalStack S3
```

### 4. Build sandbox images

```bash
make build-sandbox
```

### 5. Run the application

```bash
# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open http://localhost:5173

---

## Phase 2 — Deploy to AWS

### Step 1: Create IAM role for EC2

```bash
# Create the role
aws iam create-role \
  --role-name NebulIDE-EC2Role \
  --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Attach the Nebula IDE policy
aws iam put-role-policy \
  --role-name NebulIDE-EC2Role \
  --policy-name NebulIDEPolicy \
  --policy-document file://infrastructure/iam/ec2-instance-policy.json

# Create instance profile
aws iam create-instance-profile --instance-profile-name NebulIDE-EC2Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name NebulIDE-EC2Profile \
  --role-name NebulIDE-EC2Role
```

### Step 2: Store secrets in SSM Parameter Store

```bash
# These are encrypted at rest and fetched by ec2-bootstrap.sh at startup
aws ssm put-parameter \
  --name "/nebula-ide/SECRET_KEY" \
  --value "$(openssl rand -hex 32)" \
  --type SecureString

aws ssm put-parameter \
  --name "/nebula-ide/ANTHROPIC_API_KEY" \
  --value "sk-ant-YOUR_KEY_HERE" \
  --type SecureString

aws ssm put-parameter \
  --name "/nebula-ide/CLOUDFRONT_URL" \
  --value "https://YOUR_CLOUDFRONT_DOMAIN.cloudfront.net" \
  --type String
```

### Step 3: Launch EC2 instance

```bash
# t3.micro = free tier eligible, sufficient for development/demo
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \  # Amazon Linux 2023 us-east-1
  --instance-type t3.micro \
  --key-name YOUR_KEY_PAIR \
  --iam-instance-profile Name=NebulIDE-EC2Profile \
  --security-groups nebula-ide-sg \
  --user-data file://infrastructure/scripts/ec2-bootstrap.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=nebula-ide}]'
```

**Security group rules (inbound):**
| Port | Source    | Purpose          |
|------|-----------|------------------|
| 22   | Your IP   | SSH              |
| 80   | 0.0.0.0/0 | HTTP → HTTPS redirect |
| 443  | 0.0.0.0/0 | HTTPS API        |

### Step 4: Set up DynamoDB tables and S3

```bash
make setup-aws
```

### Step 5: Set up HTTPS on EC2

```bash
ssh -i YOUR_KEY.pem ubuntu@YOUR_EC2_IP

# Replace YOUR_DOMAIN with your actual domain or EC2 public DNS
sudo certbot --nginx -d YOUR_DOMAIN

# Update nginx config with your domain
sudo sed -i 's/YOUR_DOMAIN_HERE/YOUR_DOMAIN/g' /etc/nginx/sites-available/nebula-ide.conf
sudo nginx -t && sudo systemctl reload nginx
```

### Step 6: Deploy frontend

```bash
# Create S3 bucket for frontend
aws s3 mb s3://nebula-ide-frontend-YOUR_SUFFIX

# Enable static hosting
aws s3 website s3://nebula-ide-frontend-YOUR_SUFFIX \
  --index-document index.html --error-document index.html

# Build and deploy
S3_BUCKET=nebula-ide-frontend-YOUR_SUFFIX make deploy-frontend
```

### Step 7: Create CloudFront distribution

Follow the reference config in `infrastructure/monitoring/cloudfront-config.json`.

Key settings:
- **Price class**: `PriceClass_100` (US/EU only — cheapest)
- **API behavior**: `/api/*` → EC2 origin, caching disabled
- **Default behavior**: `*` → S3 origin, caching optimised

---

## CI/CD Setup (GitHub Actions)

Add these secrets to your GitHub repository (`Settings → Secrets → Actions`):

| Secret | Value |
|--------|-------|
| `AWS_DEPLOY_ROLE_ARN` | ARN of your deploy IAM role |
| `S3_FRONTEND_BUCKET` | Frontend S3 bucket name |
| `CLOUDFRONT_DIST_ID` | CloudFront distribution ID |
| `EC2_HOST` | EC2 public IP or hostname |
| `EC2_SSH_KEY` | Contents of your EC2 `.pem` key |

Push to `main` to trigger automatic deploy.

---

## Cost monitoring

**Set a billing alarm immediately:**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "NebulIDE-BillingAlert-30" \
  --alarm-description "Alert when AWS bill exceeds $30" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 30 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:YOUR_ACCOUNT:billing-alert \
  --dimensions Name=Currency,Value=USD
```

**Stop EC2 when not using it:**
```bash
# Stop (preserves EBS, no compute cost)
aws ec2 stop-instances --instance-ids YOUR_INSTANCE_ID

# Start again
aws ec2 start-instances --instance-ids YOUR_INSTANCE_ID
```

---

## Troubleshooting

```bash
# View API logs
make logs

# Check API health
make health

# SSH into EC2
ssh -i YOUR_KEY.pem ubuntu@YOUR_EC2_IP

# View container logs on EC2
docker compose logs -f api

# Restart API on EC2
docker compose restart api
```