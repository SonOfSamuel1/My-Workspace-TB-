## Deployment Guide - Mail Agent Web App

This guide covers all deployment options for the Mail Agent Manager web application.

## Quick Links

- [Local Development](#local-development)
- [Vercel Deployment](#vercel-deployment-recommended)
- [Docker Deployment](#docker-deployment)
- [Self-Hosted Deployment](#self-hosted-deployment)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites
- Node.js 18+ (20 recommended)
- PostgreSQL database
- npm or yarn

### Setup

1. **Clone and navigate**
   ```bash
   cd web
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Configure database**
   ```env
   # PostgreSQL connection
   DATABASE_URL="postgresql://user:password@localhost:5432/mail_agents"
   ```

5. **Generate Prisma client**
   ```bash
   npm run db:generate
   ```

6. **Apply database schema**
   ```bash
   npm run db:push
   ```

7. **Seed database** (optional, for demo data)
   ```bash
   npm run db:seed
   ```

8. **Start development server**
   ```bash
   npm run dev
   ```

9. **Open browser**
   Visit: http://localhost:3000

---

## Vercel Deployment (Recommended)

### Why Vercel?
- ✅ Zero-config deployment
- ✅ Automatic HTTPS
- ✅ Global CDN
- ✅ Serverless functions
- ✅ Free tier available
- ✅ Built by Next.js creators

### Prerequisites
- Vercel account (free)
- PostgreSQL database (Supabase/Neon recommended)
- GitHub repository

### Step-by-Step

#### 1. Database Setup (choose one)

**Option A: Supabase (Recommended)**
```bash
1. Go to https://supabase.com
2. Create new project
3. Wait for provisioning (~2 minutes)
4. Go to Settings → Database
5. Copy "Connection string" (Pooling mode)
```

**Option B: Neon**
```bash
1. Go to https://neon.tech
2. Create new project
3. Copy connection string
```

#### 2. Deploy to Vercel

**Via Vercel Dashboard:**
```bash
1. Go to https://vercel.com
2. Click "Add New Project"
3. Import your GitHub repo
4. Set root directory: "web"
5. Add environment variables (see below)
6. Click "Deploy"
```

**Via Vercel CLI:**
```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to web directory
cd web

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

#### 3. Configure Environment Variables

In Vercel dashboard (Settings → Environment Variables):

```env
# Database
DATABASE_URL=postgresql://[user]:[password]@[host]/[database]?sslmode=require

# NextAuth (CRITICAL: Generate new secret!)
NEXTAUTH_SECRET=[run: openssl rand -base64 32]
NEXTAUTH_URL=https://your-app.vercel.app

# Integration API
INTEGRATION_API_KEY=[run: openssl rand -base64 32]

# OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_ID=your-github-client-id
GITHUB_SECRET=your-github-client-secret

# Public
NEXT_PUBLIC_APP_URL=https://your-app.vercel.app
```

#### 4. Run Database Migration

After first deployment:

```bash
# Option A: Via Vercel CLI
vercel env pull .env.local
npm run db:push

# Option B: Via Vercel dashboard terminal
# Go to your deployment → More → Open in new tab → Terminal
npx prisma db push
```

#### 5. Seed Database (Optional)

```bash
npm run db:seed
```

#### 6. Test Deployment

Visit: `https://your-app.vercel.app`

---

## Docker Deployment

### Quick Start

1. **Clone repository**
   ```bash
   git clone <repo-url>
   cd web
   ```

2. **Configure environment**
   ```bash
   # Edit docker-compose.yml with your secrets
   # Or use .env file
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **View logs**
   ```bash
   docker-compose logs -f web
   ```

5. **Stop services**
   ```bash
   docker-compose down
   ```

### Production Docker Setup

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
      NEXTAUTH_URL: ${NEXTAUTH_URL}
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    restart: always
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - web

volumes:
  postgres_data:
```

### Docker Commands

```bash
# Build image
docker build -t mail-agent-web .

# Run container
docker run -p 3000:3000 \
  -e DATABASE_URL="your-db-url" \
  -e NEXTAUTH_SECRET="your-secret" \
  mail-agent-web

# Push to registry
docker tag mail-agent-web your-registry/mail-agent-web:latest
docker push your-registry/mail-agent-web:latest
```

---

## Self-Hosted Deployment

### VPS/Server Setup

#### Prerequisites
- Ubuntu 22.04 LTS (or similar)
- Node.js 20
- PostgreSQL 16
- Nginx
- Domain name with SSL

#### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Nginx
sudo apt install -y nginx

# Install PM2 (process manager)
sudo npm install -g pm2
```

#### 2. Setup PostgreSQL

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE mail_agents;
CREATE USER mail_agent WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE mail_agents TO mail_agent;
\q
```

#### 3. Clone and Setup App

```bash
# Clone repository
git clone <repo-url> /var/www/mail-agent
cd /var/www/mail-agent/web

# Install dependencies
npm ci

# Setup environment
cp .env.example .env
nano .env  # Edit with your config

# Build application
npm run build

# Run database migration
npm run db:push

# Seed database (optional)
npm run db:seed
```

#### 4. Setup PM2

```bash
# Start application
pm2 start npm --name "mail-agent-web" -- start

# Save PM2 config
pm2 save

# Setup PM2 to start on boot
pm2 startup systemd
```

#### 5. Configure Nginx

```nginx
# /etc/nginx/sites-available/mail-agent

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/mail-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. Setup SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

---

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `NEXTAUTH_SECRET` | Secret for NextAuth.js (32+ chars) | Generate with `openssl rand -base64 32` |
| `NEXTAUTH_URL` | Full URL of your app | `https://your-app.com` |
| `INTEGRATION_API_KEY` | API key for CLI integration | Generate with `openssl rand -base64 32` |

### Optional Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `GITHUB_ID` | GitHub OAuth app ID |
| `GITHUB_SECRET` | GitHub OAuth app secret |
| `NEXT_PUBLIC_APP_URL` | Public app URL (for SSE) |

### Generating Secrets

```bash
# NextAuth secret
openssl rand -base64 32

# Integration API key
openssl rand -base64 32
```

---

## Database Setup

### PostgreSQL Connection String Format

```
postgresql://[user]:[password]@[host]:[port]/[database]?[options]
```

### Local Development
```
postgresql://localhost:5432/mail_agents
```

### Production (with SSL)
```
postgresql://user:pass@host.db.com:5432/mail_agents?sslmode=require
```

### Database Providers

**Supabase:**
- Free tier: 500MB database
- Auto backups
- Built-in connection pooling
- URL format: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`

**Neon:**
- Free tier: 10GB storage
- Serverless architecture
- Branching support
- URL format: `postgresql://[user]:[password]@[endpoint].neon.tech/neondb`

**Railway:**
- Simple setup
- PostgreSQL plugin
- Auto-provisioning

---

## Troubleshooting

### Build Errors

**"Cannot find module '@prisma/client'"**
```bash
npm run db:generate
```

**"P1001: Can't reach database"**
- Check DATABASE_URL is correct
- Verify database is running
- Check firewall rules

### Runtime Errors

**"NEXTAUTH_SECRET is not set"**
```bash
# Generate and add to .env
openssl rand -base64 32
```

**"Failed to fetch"**
- Check NEXTAUTH_URL matches your deployment URL
- Verify CORS settings
- Check API endpoint is accessible

### Database Issues

**Migrations not applying**
```bash
# Reset and reapply
npm run db:push

# Or create proper migration
npm run db:migrate
```

**Connection pool exhausted**
```env
# Add to DATABASE_URL
?connection_limit=10&pool_timeout=30
```

### Performance Issues

**Slow page loads**
- Enable caching in Vercel/CDN
- Optimize database queries
- Add database indexes

**High memory usage**
- Reduce connection pool size
- Implement pagination
- Optimize images

---

## Post-Deployment Checklist

- [ ] Database is accessible and migrations applied
- [ ] Environment variables are set correctly
- [ ] HTTPS is enabled (production)
- [ ] OAuth providers configured (if using)
- [ ] Integration API key generated and secure
- [ ] Backups configured (database)
- [ ] Monitoring set up (optional)
- [ ] Error tracking enabled (optional)
- [ ] Test all major flows work
- [ ] Demo user created (for testing)

---

## Monitoring & Maintenance

### Vercel
- Built-in analytics
- Error tracking in dashboard
- Performance insights

### Self-Hosted
```bash
# View PM2 logs
pm2 logs mail-agent-web

# Monitor processes
pm2 monit

# Restart application
pm2 restart mail-agent-web

# Update application
cd /var/www/mail-agent/web
git pull
npm install
npm run build
npm run db:push
pm2 restart mail-agent-web
```

### Database Backups

**Automated (Supabase/Neon):**
- Automatic daily backups
- Point-in-time recovery

**Manual (PostgreSQL):**
```bash
# Backup
pg_dump -U mail_agent mail_agents > backup.sql

# Restore
psql -U mail_agent mail_agents < backup.sql
```

---

## Scaling Considerations

### Horizontal Scaling
- Multiple Next.js instances behind load balancer
- Shared database with connection pooling
- Redis for session storage

### Vertical Scaling
- Increase database resources
- Optimize queries with indexes
- Implement caching layer

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_emails_agent_id ON "Email"("agentId");
CREATE INDEX idx_emails_tier ON "Email"("tier");
CREATE INDEX idx_emails_status ON "Email"("status");
CREATE INDEX idx_emails_received_at ON "Email"("receivedAt");
```

---

## Security Best Practices

1. **Secrets**
   - Never commit secrets to Git
   - Use environment variables
   - Rotate keys regularly

2. **Database**
   - Use SSL connections
   - Restrict network access
   - Regular backups

3. **Application**
   - Keep dependencies updated
   - Enable CORS properly
   - Implement rate limiting

4. **Infrastructure**
   - Use HTTPS only
   - Configure security headers
   - Enable firewall rules

---

## Support

For deployment issues:
1. Check logs (Vercel dashboard or `pm2 logs`)
2. Review environment variables
3. Test database connectivity
4. Consult troubleshooting section above
5. Open GitHub issue with details

## Resources

- [Next.js Deployment Docs](https://nextjs.org/docs/deployment)
- [Prisma Deployment Guide](https://www.prisma.io/docs/guides/deployment)
- [Vercel Documentation](https://vercel.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
