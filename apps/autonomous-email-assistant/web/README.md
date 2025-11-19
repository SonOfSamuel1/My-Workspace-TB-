# Mail Agent Manager - Web Application

A beautiful, modern web application for managing autonomous email agents. Built with Next.js 15, TypeScript, Prisma, and tRPC.

## Features

- **Agent Management**: Create, configure, and monitor multiple email agents
- **Real-time Dashboard**: View email processing activity, tier distribution, and agent statistics
- **Approval Workflow**: Review and approve Tier 3 draft responses before sending
- **Email Monitoring**: Track all processed emails with filtering and search
- **Analytics**: Visualize email processing trends, response times, and costs
- **Multi-user Support**: Secure authentication with NextAuth.js
- **Type-safe API**: Full-stack type safety with tRPC

## Tech Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **API**: tRPC for type-safe API calls
- **Auth**: NextAuth.js v5
- **UI**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts for analytics visualization
- **State Management**: TanStack Query (React Query)

## Prerequisites

- Node.js 18+
- PostgreSQL database (local or hosted on Supabase/Neon)
- npm or yarn

## Getting Started

### 1. Install Dependencies

\`\`\`bash
npm install
\`\`\`

### 2. Set Up Environment Variables

Copy the example environment file:

\`\`\`bash
cp .env.example .env
\`\`\`

Edit \`.env\` and configure your database and auth settings.

### 3. Set Up Database

\`\`\`bash
# Generate Prisma Client
npx prisma generate

# Run migrations
npx prisma db push
\`\`\`

### 4. Run Development Server

\`\`\`bash
npm run dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) to see the application.

## Project Structure

See full documentation in the README for details on:
- Database schema
- API routes (tRPC)
- Authentication setup
- Deployment options

## License

MIT
