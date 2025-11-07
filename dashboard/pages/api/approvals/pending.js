/**
 * Pending Approvals API endpoint
 * Returns drafts awaiting approval
 */

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // In production, fetch from database
    const approvals = {
      count: 3,
      items: [
        {
          id: 'draft_001',
          emailId: 'email_002',
          from: 'support@vendor.com',
          to: 'support@vendor.com',
          subject: 'Re: Technical Support Request #12345',
          draft: 'Thank you for reaching out. I\'ve reviewed your support request #12345 and can confirm that the issue has been addressed in our latest release...',
          createdAt: new Date(Date.now() - 1000 * 60 * 32).toISOString(),
          priority: 'normal',
          estimatedSendTime: new Date(Date.now() + 1000 * 60 * 60).toISOString()
        },
        {
          id: 'draft_002',
          emailId: 'email_006',
          from: 'team@internal.com',
          to: 'team@internal.com',
          subject: 'Re: Project Status Update',
          draft: 'Thanks for the update. The project timeline looks good. Please proceed with the next phase and keep me posted on any blockers...',
          createdAt: new Date(Date.now() - 1000 * 60 * 102).toISOString(),
          priority: 'low',
          estimatedSendTime: new Date(Date.now() + 1000 * 60 * 120).toISOString()
        },
        {
          id: 'draft_003',
          emailId: 'email_005',
          from: 'partner@company.com',
          to: 'partner@company.com',
          subject: 'Re: Partnership Proposal - Q1 2024',
          draft: 'Thank you for sharing the Q1 partnership proposal. I\'ve reviewed the details and would like to schedule a call to discuss the terms further...',
          createdAt: new Date(Date.now() - 1000 * 60 * 89).toISOString(),
          priority: 'high',
          estimatedSendTime: new Date(Date.now() + 1000 * 60 * 30).toISOString()
        }
      ]
    };

    res.status(200).json(approvals);
  } catch (error) {
    console.error('Error fetching pending approvals:', error);
    res.status(500).json({ error: 'Failed to fetch pending approvals' });
  }
}
