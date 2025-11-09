-- AlterTable
ALTER TABLE "Email" ADD COLUMN     "cc" TEXT,
ADD COLUMN     "bcc" TEXT,
ADD COLUMN     "replyTo" TEXT,
ADD COLUMN     "bodyHtml" TEXT,
ADD COLUMN     "headers" JSONB,
ADD COLUMN     "attachments" JSONB,
ADD COLUMN     "inReplyTo" TEXT,
ADD COLUMN     "references" TEXT;
