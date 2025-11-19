/**
 * Recent Emails API endpoint
 * Returns list of recently processed emails
 */

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const limit = parseInt(req.query.limit) || 20;

    // In production, fetch from database
    const emails = {
      items: [
        {
          id: 'email_001',
          from: 'client@example.com',
          subject: 'Q4 Budget Review Meeting',
          date: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
          tier: 2,
          action: 'handled',
          sentiment: { emotion: 'neutral', urgency: 'medium' },
          hasAttachments: true,
          threadId: 'thread_001'
        },
        {
          id: 'email_002',
          from: 'support@vendor.com',
          subject: 'Re: Technical Support Request #12345',
          date: new Date(Date.now() - 1000 * 60 * 32).toISOString(),
          tier: 3,
          action: 'draft_created',
          sentiment: { emotion: 'positive', urgency: 'low' },
          hasAttachments: false,
          threadId: 'thread_002'
        },
        {
          id: 'email_003',
          from: 'ceo@company.com',
          subject: 'URGENT: Board Meeting Prep',
          date: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
          tier: 1,
          action: 'escalated',
          sentiment: { emotion: 'urgent', urgency: 'high' },
          hasAttachments: true,
          threadId: 'thread_003'
        },
        {
          id: 'email_004',
          from: 'newsletter@industry.com',
          subject: 'Weekly Industry Updates',
          date: new Date(Date.now() - 1000 * 60 * 67).toISOString(),
          tier: 4,
          action: 'flagged',
          sentiment: { emotion: 'neutral', urgency: 'low' },
          hasAttachments: false,
          threadId: 'thread_004'
        },
        {
          id: 'email_005',
          from: 'partner@company.com',
          subject: 'Partnership Proposal - Q1 2024',
          date: new Date(Date.now() - 1000 * 60 * 89).toISOString(),
          tier: 2,
          action: 'handled',
          sentiment: { emotion: 'positive', urgency: 'medium' },
          hasAttachments: true,
          threadId: 'thread_005'
        },
        {
          id: 'email_006',
          from: 'team@internal.com',
          subject: 'Project Status Update',
          date: new Date(Date.now() - 1000 * 60 * 102).toISOString(),
          tier: 3,
          action: 'draft_created',
          sentiment: { emotion: 'neutral', urgency: 'low' },
          hasAttachments: false,
          threadId: 'thread_006'
        }
      ].slice(0, limit),
      total: 312,
      page: 1,
      limit: limit
    };

    res.status(200).json(emails);
  } catch (error) {
    console.error('Error fetching emails:', error);
    res.status(500).json({ error: 'Failed to fetch emails' });
  }
}
