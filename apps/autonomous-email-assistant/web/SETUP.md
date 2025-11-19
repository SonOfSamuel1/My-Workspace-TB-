# Setup Guide - Mail Agent Manager Web App

This guide will walk you through setting up the Mail Agent Manager web application from scratch.

## Quick Start (Development)

```bash
cd web
npm install
cp .env.example .env
# Edit .env with your database URL
npx prisma db push
npm run dev
```

## Detailed Setup

### Step 1: Prerequisites

Ensure you have the following installed:
- Node.js 18 or higher
- npm or yarn
- PostgreSQL (local or cloud)

### Step 2: Database Setup

#### Option A: Local PostgreSQL

```bash
# Install PostgreSQL (macOS)
brew install postgresql@16
brew services start postgresql@16

# Create database
createdb mail_agents

# Connection string
DATABASE_URL="postgresql://localhost:5432/mail_agents"
```

#### Option B: Supabase (Recommended for beginners)

1. Go to [supabase.com](https://supabase.com) and create account
2. Create new project (choose a region close to you)
3. Wait for provisioning (~2 minutes)
4. Go to Settings > Database
5. Copy "Connection string" under "Connection pooling"
6. Use that as your `DATABASE_URL`

```env
DATABASE_URL="postgresql://postgres.xxx:[YOUR-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
```

#### Option C: Neon (Free serverless PostgreSQL)

1. Go to [neon.tech](https://neon.tech) and create account
2. Create new project
3. Copy the connection string
4. Use it as your `DATABASE_URL`

### Step 3: Environment Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required: Database
DATABASE_URL="your-postgres-connection-string"

# Required: NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="run: openssl rand -base64 32"

# Optional: OAuth (add if you want Google/GitHub login)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
GITHUB_ID=""
GITHUB_SECRET=""
```

### Step 4: Generate NextAuth Secret

```bash
openssl rand -base64 32
```

Copy the output to `NEXTAUTH_SECRET` in `.env`.

### Step 5: Install Dependencies

```bash
npm install
```

This will install:
- Next.js and React
- Prisma (database)
- tRPC (API)
- NextAuth (authentication)
- Tailwind CSS and UI components

### Step 6: Set Up Database

```bash
# Generate Prisma Client (creates type-safe database client)
npx prisma generate

# Push schema to database (creates tables)
npx prisma db push
```

You should see output like:
```
Your database is now in sync with your Prisma schema.
✔ Generated Prisma Client
```

### Step 7: (Optional) View Database

```bash
npx prisma studio
```

This opens a visual database browser at http://localhost:5555.

### Step 8: Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

You should see the dashboard (empty state since no agents exist yet).

## Setting Up OAuth (Optional)

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project
3. Enable "Google+ API"
4. Go to "Credentials" > "Create Credentials" > "OAuth client ID"
5. Choose "Web application"
6. Add Authorized redirect URI:
   - `http://localhost:3000/api/auth/callback/google` (development)
   - `https://yourdomain.com/api/auth/callback/google` (production)
7. Copy Client ID and Client Secret to `.env`

### GitHub OAuth

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Click "New OAuth App"
3. Fill in:
   - Application name: Mail Agent Manager
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:3000/api/auth/callback/github`
4. Click "Register application"
5. Generate a new client secret
6. Copy Client ID and Client Secret to `.env`

## Troubleshooting

### "Cannot find module '@prisma/client'"

Run:
```bash
npx prisma generate
```

### "Error: P1001: Can't reach database server"

- Check your `DATABASE_URL` is correct
- Ensure PostgreSQL is running (if local)
- Check firewall rules (if cloud database)

### "Invalid `prisma.user.findUnique()` invocation"

Your database schema is out of sync. Run:
```bash
npx prisma db push
```

### "NEXTAUTH_SECRET is not set"

Generate a secret:
```bash
openssl rand -base64 32
```

Add it to `.env` as `NEXTAUTH_SECRET`.

### Port 3000 is already in use

Either:
- Kill the process using port 3000: `lsof -ti:3000 | xargs kill -9`
- Use a different port: `PORT=3001 npm run dev`

## Next Steps

1. **Create your first agent**: Go to dashboard and click "Create Agent"
2. **Configure agent settings**: Set timezone, business hours, and tier rules
3. **Connect Gmail**: Follow the Gmail MCP integration guide in the parent project
4. **Test the system**: Send a test email and watch it appear in the dashboard

## Development Workflow

### Making Schema Changes

1. Edit `prisma/schema.prisma`
2. Run `npx prisma db push` (development)
3. Or create migration: `npx prisma migrate dev --name describe_changes`

### Adding New API Routes

1. Create router in `src/server/routers/your-router.ts`
2. Add to `src/server/routers/_app.ts`
3. Use in components with `trpc.yourRouter.yourProcedure.useQuery()`

### Adding UI Components

```bash
# Using shadcn/ui
npx shadcn@latest add [component-name]

# Example
npx shadcn@latest add button
npx shadcn@latest add dialog
npx shadcn@latest add table
```

## Production Deployment

See main README.md for deployment instructions to:
- Vercel (recommended)
- Docker
- Self-hosted

## Getting Help

- Check the main README.md for detailed documentation
- Open an issue on GitHub
- Review Prisma docs: https://www.prisma.io/docs
- Review tRPC docs: https://trpc.io
- Review Next.js docs: https://nextjs.org/docs
