# Database Migration Guide

This guide explains how to manage database migrations for the Mail Agents web application.

## Overview

We use Prisma Migrate for database schema management. This provides:
- Version-controlled database changes
- Rollback capabilities
- Safe production deployments
- Team synchronization

## Development Workflow

### 1. Create a New Migration

When you modify `prisma/schema.prisma`:

```bash
# Generate migration files (don't apply yet)
npm run db:migrate:create

# This creates a new migration in prisma/migrations/
# Review the SQL before applying
```

### 2. Apply Migrations

```bash
# Apply all pending migrations to your dev database
npm run db:migrate

# This runs:
# - Executes pending migrations
# - Generates Prisma Client
# - Updates your database
```

### 3. Reset Database (Development Only)

```bash
# Drop database, recreate, apply all migrations, run seed
npm run db:reset

# WARNING: This deletes ALL data
```

## Production Deployment

### Option 1: Automatic Migrations (Vercel, etc.)

Add to your build command:
```bash
npx prisma migrate deploy && npm run build
```

This safely applies pending migrations without prompts.

### Option 2: Manual Migrations

```bash
# Review pending migrations
npx prisma migrate status

# Apply migrations
npx prisma migrate deploy
```

### Option 3: Docker Deployment

The `docker-compose.yml` already handles migrations:
```yaml
command: sh -c "npx prisma migrate deploy && npm start"
```

## Migration Best Practices

### 1. Never Edit Generated Migrations

Once a migration is committed, don't modify it. Create a new migration instead.

### 2. Test Migrations Before Production

```bash
# Create a production-like database
createdb mail_agents_staging

# Test migration
DATABASE_URL="postgresql://..." npx prisma migrate deploy

# Verify schema
npx prisma db pull
```

### 3. Handle Data Migrations

For complex changes (e.g., splitting columns), use a multi-step approach:

**Step 1**: Add new column (nullable)
```bash
npx prisma migrate dev --name add_new_column
```

**Step 2**: Copy data (use a script)
```typescript
// scripts/migrate-data.ts
const users = await prisma.user.findMany()
for (const user of users) {
  await prisma.user.update({
    where: { id: user.id },
    data: { newColumn: transformOldColumn(user.oldColumn) }
  })
}
```

**Step 3**: Make column required
```bash
npx prisma migrate dev --name make_column_required
```

**Step 4**: Remove old column
```bash
npx prisma migrate dev --name remove_old_column
```

### 4. Soft Deletes

The schema now includes `deletedAt` fields. Update queries:

```typescript
// ✅ Correct: Exclude soft-deleted records
const agents = await prisma.agent.findMany({
  where: {
    userId,
    deletedAt: null, // Only active records
  }
})

// ❌ Incorrect: Returns deleted records
const agents = await prisma.agent.findMany({
  where: { userId }
})
```

### 5. Rolling Back Migrations

If a migration fails:

```bash
# Revert to previous migration
npx prisma migrate resolve --rolled-back 20250109_migration_name

# Fix the schema
# Create a new migration
npx prisma migrate dev --name fix_previous_migration
```

## Common Scenarios

### Adding a New Model

1. Add model to `schema.prisma`
2. Create migration: `npm run db:migrate:create`
3. Review generated SQL
4. Apply: `npm run db:migrate`
5. Update seed file if needed

### Adding an Index

```prisma
model Email {
  // ... fields
  @@index([agentId, receivedAt]) // Composite index
}
```

Then run:
```bash
npm run db:migrate:create
# Migration will include CREATE INDEX statement
npm run db:migrate
```

### Changing Column Type

**Safe approach** (no data loss):

```prisma
model User {
  // Change from String to Int
  age String // Old
  age Int     // New - Requires data migration!
}
```

1. Create migration: `npm run db:migrate:create`
2. **Edit migration** to handle data conversion:

```sql
-- Migration
ALTER TABLE "User" ADD COLUMN "age_new" INTEGER;
UPDATE "User" SET "age_new" = CAST("age" AS INTEGER) WHERE "age" ~ '^[0-9]+$';
ALTER TABLE "User" DROP COLUMN "age";
ALTER TABLE "User" RENAME COLUMN "age_new" TO "age";
```

3. Apply: `npm run db:migrate`

### Renaming Columns

Prisma can't detect renames, so it drops and recreates (losing data). Use custom SQL:

```sql
-- Instead of generated DROP + ADD
ALTER TABLE "User" RENAME COLUMN "name" TO "full_name";
```

## Troubleshooting

### "Migration failed to apply"

```bash
# Check migration status
npx prisma migrate status

# Mark as applied if already run manually
npx prisma migrate resolve --applied 20250109_migration_name

# Or roll back
npx prisma migrate resolve --rolled-back 20250109_migration_name
```

### "Database schema is not in sync"

```bash
# Reset to latest migration
npx prisma migrate reset

# Or pull current schema
npx prisma db pull
npx prisma generate
```

### "Out of sync with migrations"

```bash
# Generate client from schema
npx prisma generate

# If schema differs from database
npx prisma migrate dev --name sync_schema
```

## CI/CD Integration

### GitHub Actions

Already configured in `.github/workflows/web-app-ci.yml`:

```yaml
- name: Run Database Migrations
  run: npx prisma migrate deploy
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Vercel

Add to `vercel.json`:
```json
{
  "buildCommand": "npx prisma migrate deploy && npm run build",
  "env": {
    "DATABASE_URL": "@database_url"
  }
}
```

## Schema Change Checklist

Before deploying schema changes:

- [ ] Migration created and reviewed
- [ ] Data migration script written (if needed)
- [ ] Tested on staging database
- [ ] Backup production database
- [ ] Deploy during low-traffic window
- [ ] Monitor application logs
- [ ] Verify data integrity
- [ ] Update API documentation if schema changes affect APIs

## Package.json Scripts

```json
{
  "db:migrate": "prisma migrate dev",
  "db:migrate:create": "prisma migrate dev --create-only",
  "db:migrate:deploy": "prisma migrate deploy",
  "db:migrate:status": "prisma migrate status",
  "db:reset": "prisma migrate reset",
  "db:seed": "tsx prisma/seed.ts",
  "db:studio": "prisma studio"
}
```

## Additional Resources

- [Prisma Migrate Docs](https://www.prisma.io/docs/concepts/components/prisma-migrate)
- [Production Best Practices](https://www.prisma.io/docs/guides/deployment/production-best-practices)
- [Schema Prototyping](https://www.prisma.io/docs/guides/database/prototyping-schema-db-push)
