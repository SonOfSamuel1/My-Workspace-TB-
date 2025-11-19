-- CreateTable
CREATE TABLE "SavedEmailSearch" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "filters" JSONB NOT NULL,
    "usageCount" INTEGER NOT NULL DEFAULT 0,
    "lastUsedAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "SavedEmailSearch_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "SavedEmailSearch_userId_idx" ON "SavedEmailSearch"("userId");

-- CreateIndex
CREATE INDEX "SavedEmailSearch_userId_usageCount_idx" ON "SavedEmailSearch"("userId", "usageCount");

-- AddForeignKey
ALTER TABLE "SavedEmailSearch" ADD CONSTRAINT "SavedEmailSearch_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
