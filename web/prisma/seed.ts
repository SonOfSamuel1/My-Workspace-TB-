import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  console.log('🌱 Seeding database...')

  // Create a test user
  const user = await prisma.user.upsert({
    where: { email: 'demo@example.com' },
    update: {},
    create: {
      email: 'demo@example.com',
      name: 'Demo User',
    },
  })

  console.log('✅ Created user:', user.email)

  // Create sample agents
  const agent1 = await prisma.agent.upsert({
    where: { agentEmail: 'executive@demo.com' },
    update: {},
    create: {
      userId: user.id,
      name: 'Executive Assistant',
      agentEmail: 'executive@demo.com',
      description: 'Main executive email assistant handling all business correspondence',
      enabled: true,
      gmailConnected: true,
      gmailEmail: 'executive@demo.com',
      config: {
        timezone: 'America/New_York',
        businessHours: {
          start: 9,
          end: 17,
        },
        communicationStyle: 'professional',
        offLimitsContacts: ['ceo@company.com', 'board@company.com'],
        tierRules: {
          tier1Keywords: ['urgent', 'asap', 'emergency'],
          tier2AutoReply: true,
        },
      },
      lastRunAt: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
    },
  })

  const agent2 = await prisma.agent.upsert({
    where: { agentEmail: 'support@demo.com' },
    update: {},
    create: {
      userId: user.id,
      name: 'Customer Support Agent',
      agentEmail: 'support@demo.com',
      description: 'Handles customer inquiries and support requests',
      enabled: true,
      gmailConnected: false,
      config: {
        timezone: 'America/Los_Angeles',
        businessHours: {
          start: 8,
          end: 18,
        },
        communicationStyle: 'friendly',
        offLimitsContacts: [],
      },
    },
  })

  console.log('✅ Created agents:', agent1.name, agent2.name)

  // Create sample emails for agent1
  const emails = await Promise.all([
    // Tier 1 - Escalation
    prisma.email.create({
      data: {
        agentId: agent1.id,
        gmailId: 'msg-001',
        gmailThreadId: 'thread-001',
        subject: 'URGENT: Board Meeting Canceled',
        from: 'ceo@company.com',
        to: 'executive@demo.com',
        snippet: 'The board meeting scheduled for tomorrow has been canceled...',
        body: 'The board meeting scheduled for tomorrow has been canceled due to unforeseen circumstances. Please notify all stakeholders immediately.',
        tier: 1,
        reasoning: 'Email from CEO (off-limits contact) with urgent subject matter. Requires immediate escalation.',
        confidence: 0.95,
        status: 'escalated',
        receivedAt: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
        processedAt: new Date(Date.now() - 1000 * 60 * 60 * 2 + 1000 * 30), // 30 seconds after
        processed: true,
      },
    }),

    // Tier 2 - Auto-handled
    prisma.email.create({
      data: {
        agentId: agent1.id,
        gmailId: 'msg-002',
        gmailThreadId: 'thread-002',
        subject: 'Weekly Report Request',
        from: 'analyst@company.com',
        to: 'executive@demo.com',
        snippet: 'Can you send me the weekly analytics report?',
        body: 'Hi,\n\nCan you send me the weekly analytics report for review?\n\nThanks!',
        tier: 2,
        reasoning: 'Routine request for standard report. Can be handled autonomously with template response.',
        confidence: 0.88,
        status: 'processed',
        receivedAt: new Date(Date.now() - 1000 * 60 * 90), // 1.5 hours ago
        processedAt: new Date(Date.now() - 1000 * 60 * 88),
        processed: true,
      },
    }),

    // Tier 3 - Draft for approval
    prisma.email.create({
      data: {
        agentId: agent1.id,
        gmailId: 'msg-003',
        gmailThreadId: 'thread-003',
        subject: 'Partnership Proposal',
        from: 'partnerships@techcorp.com',
        to: 'executive@demo.com',
        snippet: 'We would like to discuss a potential partnership...',
        body: 'Dear Executive,\n\nWe would like to discuss a potential partnership between our companies. We believe there are significant synergies...\n\nBest regards,\nTechCorp Partnerships',
        tier: 3,
        reasoning: 'Important partnership proposal requiring thoughtful response. Draft created for review before sending.',
        confidence: 0.82,
        status: 'pending_approval',
        receivedAt: new Date(Date.now() - 1000 * 60 * 45), // 45 minutes ago
        processedAt: new Date(Date.now() - 1000 * 60 * 43),
        processed: false,
      },
    }),

    // Tier 4 - Flag only
    prisma.email.create({
      data: {
        agentId: agent1.id,
        gmailId: 'msg-004',
        gmailThreadId: 'thread-004',
        subject: 'Newsletter Subscription',
        from: 'marketing@newsletter.com',
        to: 'executive@demo.com',
        snippet: 'Thank you for subscribing to our newsletter...',
        body: 'Thank you for subscribing to our newsletter. You will receive weekly updates...',
        tier: 4,
        reasoning: 'Marketing newsletter, informational only. No action required.',
        confidence: 0.92,
        status: 'flagged',
        receivedAt: new Date(Date.now() - 1000 * 60 * 15), // 15 minutes ago
        processedAt: new Date(Date.now() - 1000 * 60 * 14),
        processed: true,
      },
    }),

    // Another Tier 3 for approval queue
    prisma.email.create({
      data: {
        agentId: agent1.id,
        gmailId: 'msg-005',
        gmailThreadId: 'thread-005',
        subject: 'Conference Speaking Invitation',
        from: 'events@techconf.com',
        to: 'executive@demo.com',
        snippet: 'We would like to invite you to speak at TechConf 2025...',
        body: 'Dear Executive,\n\nWe would like to invite you to speak at TechConf 2025. The conference will be held...',
        tier: 3,
        reasoning: 'Speaking invitation requires personalized response. Draft prepared for approval.',
        confidence: 0.79,
        status: 'pending_approval',
        receivedAt: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
        processedAt: new Date(Date.now() - 1000 * 60 * 28),
        processed: false,
      },
    }),
  ])

  console.log('✅ Created', emails.length, 'sample emails')

  // Create sample actions
  const actions = await Promise.all([
    // SMS escalation for Tier 1
    prisma.agentAction.create({
      data: {
        agentId: agent1.id,
        emailId: emails[0].id,
        type: 'sms_sent',
        data: {
          to: '+1234567890',
          message: 'Urgent email from CEO: Board Meeting Canceled',
        },
        requiresApproval: false,
        status: 'completed',
        createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2 + 1000 * 35),
        completedAt: new Date(Date.now() - 1000 * 60 * 60 * 2 + 1000 * 36),
      },
    }),

    // Auto-response for Tier 2
    prisma.agentAction.create({
      data: {
        agentId: agent1.id,
        emailId: emails[1].id,
        type: 'response_sent',
        data: {
          responseText: 'Hi,\n\nThe weekly analytics report has been attached for your review.\n\nBest regards',
        },
        requiresApproval: false,
        status: 'completed',
        createdAt: new Date(Date.now() - 1000 * 60 * 88),
        completedAt: new Date(Date.now() - 1000 * 60 * 87),
      },
    }),

    // Draft for Tier 3
    prisma.agentAction.create({
      data: {
        agentId: agent1.id,
        emailId: emails[2].id,
        type: 'draft_created',
        data: {
          responseText:
            'Dear TechCorp Partnerships Team,\n\nThank you for reaching out regarding a potential partnership. I am very interested in exploring this opportunity.\n\nCould we schedule a call next week to discuss the details further?\n\nBest regards',
        },
        requiresApproval: true,
        approved: null,
        status: 'pending',
        createdAt: new Date(Date.now() - 1000 * 60 * 43),
      },
    }),

    // Another draft
    prisma.agentAction.create({
      data: {
        agentId: agent1.id,
        emailId: emails[4].id,
        type: 'draft_created',
        data: {
          responseText:
            'Dear TechConf Events Team,\n\nThank you for the speaking invitation. I would be honored to participate in TechConf 2025.\n\nPlease send me more details about the session format and available time slots.\n\nLooking forward to it!',
        },
        requiresApproval: true,
        approved: null,
        status: 'pending',
        createdAt: new Date(Date.now() - 1000 * 60 * 28),
      },
    }),
  ])

  console.log('✅ Created', actions.length, 'sample actions')

  // Create analytics data
  const today = new Date()
  const analytics = await Promise.all([
    // Today's analytics
    prisma.analytics.create({
      data: {
        agentId: agent1.id,
        date: today,
        emailsProcessed: 5,
        tier1Count: 1,
        tier2Count: 1,
        tier3Count: 2,
        tier4Count: 1,
        responsesSent: 1,
        draftsCreated: 2,
        escalations: 1,
        avgResponseTime: 2.5, // minutes
        claudeTokens: 15000,
        openrouterTokens: 0,
        estimatedCost: 0.45,
      },
    }),

    // Yesterday's analytics
    prisma.analytics.create({
      data: {
        agentId: agent1.id,
        date: new Date(Date.now() - 1000 * 60 * 60 * 24),
        emailsProcessed: 12,
        tier1Count: 0,
        tier2Count: 8,
        tier3Count: 3,
        tier4Count: 1,
        responsesSent: 8,
        draftsCreated: 3,
        escalations: 0,
        avgResponseTime: 3.2,
        claudeTokens: 32000,
        openrouterTokens: 5000,
        estimatedCost: 1.15,
      },
    }),

    // Analytics for agent2
    prisma.analytics.create({
      data: {
        agentId: agent2.id,
        date: today,
        emailsProcessed: 0,
        tier1Count: 0,
        tier2Count: 0,
        tier3Count: 0,
        tier4Count: 0,
        responsesSent: 0,
        draftsCreated: 0,
        escalations: 0,
        claudeTokens: 0,
        openrouterTokens: 0,
        estimatedCost: 0,
      },
    }),
  ])

  console.log('✅ Created', analytics.length, 'analytics records')

  console.log('\n🎉 Database seeded successfully!')
  console.log('\nDemo credentials:')
  console.log('  Email: demo@example.com')
  console.log('\nSample data created:')
  console.log('  - 1 user')
  console.log('  - 2 agents (Executive Assistant, Customer Support)')
  console.log('  - 5 emails (1 Tier 1, 1 Tier 2, 2 Tier 3, 1 Tier 4)')
  console.log('  - 4 actions (1 SMS, 1 response, 2 drafts)')
  console.log('  - 3 analytics records')
  console.log('\nYou can now:')
  console.log('  - View dashboard at /dashboard')
  console.log('  - Review approvals at /approvals (2 pending)')
  console.log('  - Check analytics at /analytics')
  console.log('  - Browse emails at /emails')
}

main()
  .then(async () => {
    await prisma.$disconnect()
  })
  .catch(async (e) => {
    console.error('Error seeding database:', e)
    await prisma.$disconnect()
    process.exit(1)
  })
