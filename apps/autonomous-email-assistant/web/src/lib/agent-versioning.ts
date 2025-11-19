import { prisma } from '@/lib/prisma'
import type { Prisma } from '@prisma/client'

/**
 * Agent Versioning Service
 *
 * Handles automatic snapshot creation, version tracking, and rollback capabilities
 * for agent configuration changes.
 */

export interface VersionDiff {
  field: string
  oldValue: any
  newValue: any
  type: 'added' | 'removed' | 'modified'
}

export interface VersionInfo {
  id: string
  version: number
  config: any
  changedBy?: string
  changeReason?: string
  changesSummary?: string
  createdAt: Date
}

/**
 * Create a new version snapshot when an agent config is updated
 */
export async function createVersionSnapshot(
  agentId: string,
  newConfig: any,
  userId: string,
  changeReason?: string
): Promise<VersionInfo> {
  // Get the current agent to access previous config
  const agent = await prisma.agent.findUnique({
    where: { id: agentId },
    include: {
      versions: {
        orderBy: { version: 'desc' },
        take: 1,
      },
    },
  })

  if (!agent) {
    throw new Error('Agent not found')
  }

  // Determine the next version number
  const latestVersion = agent.versions[0]?.version ?? 0
  const nextVersion = latestVersion + 1

  // Generate changes summary
  const previousConfig = agent.config as any
  const changesSummary = generateChangesSummary(previousConfig, newConfig)

  // Create the version snapshot
  const version = await prisma.agentVersion.create({
    data: {
      agentId,
      version: nextVersion,
      config: newConfig as Prisma.InputJsonValue,
      previousConfig: previousConfig as Prisma.InputJsonValue,
      changedBy: userId,
      changeReason,
      changesSummary,
    },
  })

  return {
    id: version.id,
    version: version.version,
    config: version.config,
    changedBy: version.changedBy ?? undefined,
    changeReason: version.changeReason ?? undefined,
    changesSummary: version.changesSummary ?? undefined,
    createdAt: version.createdAt,
  }
}

/**
 * Get version history for an agent
 */
export async function getVersionHistory(
  agentId: string,
  limit: number = 50
): Promise<VersionInfo[]> {
  const versions = await prisma.agentVersion.findMany({
    where: { agentId },
    orderBy: { version: 'desc' },
    take: limit,
  })

  return versions.map((v) => ({
    id: v.id,
    version: v.version,
    config: v.config,
    changedBy: v.changedBy ?? undefined,
    changeReason: v.changeReason ?? undefined,
    changesSummary: v.changesSummary ?? undefined,
    createdAt: v.createdAt,
  }))
}

/**
 * Get a specific version by version number
 */
export async function getVersion(
  agentId: string,
  version: number
): Promise<VersionInfo | null> {
  const versionRecord = await prisma.agentVersion.findUnique({
    where: {
      agentId_version: {
        agentId,
        version,
      },
    },
  })

  if (!versionRecord) return null

  return {
    id: versionRecord.id,
    version: versionRecord.version,
    config: versionRecord.config,
    changedBy: versionRecord.changedBy ?? undefined,
    changeReason: versionRecord.changeReason ?? undefined,
    changesSummary: versionRecord.changesSummary ?? undefined,
    createdAt: versionRecord.createdAt,
  }
}

/**
 * Rollback an agent to a specific version
 */
export async function rollbackToVersion(
  agentId: string,
  targetVersion: number,
  userId: string,
  reason?: string
): Promise<VersionInfo> {
  // Get the target version
  const targetVersionRecord = await getVersion(agentId, targetVersion)

  if (!targetVersionRecord) {
    throw new Error(`Version ${targetVersion} not found`)
  }

  // Update the agent with the old config
  await prisma.agent.update({
    where: { id: agentId },
    data: {
      config: targetVersionRecord.config as Prisma.InputJsonValue,
      updatedAt: new Date(),
    },
  })

  // Create a new version snapshot for the rollback
  const rollbackReason = reason
    ? `Rollback to version ${targetVersion}: ${reason}`
    : `Rollback to version ${targetVersion}`

  return createVersionSnapshot(
    agentId,
    targetVersionRecord.config,
    userId,
    rollbackReason
  )
}

/**
 * Compare two versions and generate a diff
 */
export async function compareVersions(
  agentId: string,
  versionA: number,
  versionB: number
): Promise<VersionDiff[]> {
  const [versionARecord, versionBRecord] = await Promise.all([
    getVersion(agentId, versionA),
    getVersion(agentId, versionB),
  ])

  if (!versionARecord || !versionBRecord) {
    throw new Error('One or both versions not found')
  }

  return generateDiff(versionARecord.config, versionBRecord.config)
}

/**
 * Generate a human-readable changes summary
 */
function generateChangesSummary(oldConfig: any, newConfig: any): string {
  const changes: string[] = []

  // Check top-level changes
  const allKeys = new Set([
    ...Object.keys(oldConfig || {}),
    ...Object.keys(newConfig || {}),
  ])

  for (const key of allKeys) {
    const oldValue = oldConfig?.[key]
    const newValue = newConfig?.[key]

    if (oldValue === undefined && newValue !== undefined) {
      changes.push(`Added ${key}`)
    } else if (oldValue !== undefined && newValue === undefined) {
      changes.push(`Removed ${key}`)
    } else if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      // Check for specific field types for better descriptions
      if (key === 'schedule') {
        changes.push('Updated business hours')
      } else if (key === 'tierRules') {
        changes.push('Modified tier classification rules')
      } else if (key === 'offLimitsContacts') {
        changes.push('Updated off-limits contacts')
      } else if (key === 'communicationStyle') {
        changes.push('Changed communication style')
      } else {
        changes.push(`Modified ${key}`)
      }
    }
  }

  return changes.length > 0 ? changes.join(', ') : 'No changes detected'
}

/**
 * Generate a detailed diff between two configs
 */
function generateDiff(oldConfig: any, newConfig: any, prefix: string = ''): VersionDiff[] {
  const diffs: VersionDiff[] = []

  const allKeys = new Set([
    ...Object.keys(oldConfig || {}),
    ...Object.keys(newConfig || {}),
  ])

  for (const key of allKeys) {
    const fieldPath = prefix ? `${prefix}.${key}` : key
    const oldValue = oldConfig?.[key]
    const newValue = newConfig?.[key]

    if (oldValue === undefined && newValue !== undefined) {
      diffs.push({
        field: fieldPath,
        oldValue: null,
        newValue,
        type: 'added',
      })
    } else if (oldValue !== undefined && newValue === undefined) {
      diffs.push({
        field: fieldPath,
        oldValue,
        newValue: null,
        type: 'removed',
      })
    } else if (typeof oldValue === 'object' && typeof newValue === 'object' && !Array.isArray(oldValue) && !Array.isArray(newValue)) {
      // Recursively diff nested objects
      diffs.push(...generateDiff(oldValue, newValue, fieldPath))
    } else if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
      diffs.push({
        field: fieldPath,
        oldValue,
        newValue,
        type: 'modified',
      })
    }
  }

  return diffs
}

/**
 * Get the latest version number for an agent
 */
export async function getLatestVersionNumber(agentId: string): Promise<number> {
  const latestVersion = await prisma.agentVersion.findFirst({
    where: { agentId },
    orderBy: { version: 'desc' },
    select: { version: true },
  })

  return latestVersion?.version ?? 0
}

/**
 * Clean up old versions (keep last N versions)
 */
export async function pruneOldVersions(
  agentId: string,
  keepCount: number = 50
): Promise<number> {
  const versions = await prisma.agentVersion.findMany({
    where: { agentId },
    orderBy: { version: 'desc' },
    select: { id: true, version: true },
  })

  if (versions.length <= keepCount) {
    return 0
  }

  const versionsToDelete = versions.slice(keepCount)
  const idsToDelete = versionsToDelete.map((v) => v.id)

  const result = await prisma.agentVersion.deleteMany({
    where: {
      id: { in: idsToDelete },
    },
  })

  return result.count
}
