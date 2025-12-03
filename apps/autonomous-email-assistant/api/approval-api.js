/**
 * Approval API - REST endpoints for managing email approvals
 * Can be deployed as Lambda with API Gateway or Express server
 */

const ApprovalQueueManager = require('../lib/database/approval-queue');
const EmailStateManager = require('../lib/database/email-state');
const logger = require('../lib/logger');

// Initialize managers
const approvalQueue = new ApprovalQueueManager();
const emailState = new EmailStateManager();

/**
 * API Response Helper
 */
function apiResponse(statusCode, body) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    },
    body: JSON.stringify(body)
  };
}

/**
 * Lambda Handler for API Gateway
 */
exports.handler = async (event, context) => {
  const { httpMethod, path, pathParameters, queryStringParameters, body } = event;

  logger.info('API request received', {
    method: httpMethod,
    path,
    params: pathParameters
  });

  try {
    // Handle CORS preflight
    if (httpMethod === 'OPTIONS') {
      return apiResponse(200, { message: 'OK' });
    }

    // Route requests
    const route = `${httpMethod} ${path}`;

    // Pending Approvals
    if (route.match(/^GET \/approvals$/)) {
      return await getPendingApprovals(queryStringParameters);
    }

    // Get specific approval
    if (route.match(/^GET \/approvals\/[^/]+$/)) {
      return await getApproval(pathParameters.id);
    }

    // Approve
    if (route.match(/^POST \/approvals\/[^/]+\/approve$/)) {
      return await approveItem(pathParameters.id, JSON.parse(body || '{}'));
    }

    // Reject
    if (route.match(/^POST \/approvals\/[^/]+\/reject$/)) {
      return await rejectItem(pathParameters.id, JSON.parse(body || '{}'));
    }

    // Bulk approve
    if (route.match(/^POST \/approvals\/bulk-approve$/)) {
      return await bulkApprove(JSON.parse(body || '{}'));
    }

    // Statistics
    if (route.match(/^GET \/stats$/)) {
      return await getStatistics(queryStringParameters);
    }

    // Dashboard data
    if (route.match(/^GET \/dashboard$/)) {
      return await getDashboardData(queryStringParameters);
    }

    // Email history
    if (route.match(/^GET \/emails$/)) {
      return await getEmailHistory(queryStringParameters);
    }

    // Get specific email
    if (route.match(/^GET \/emails\/[^/]+$/)) {
      return await getEmail(pathParameters.id);
    }

    // Submit feedback
    if (route.match(/^POST \/emails\/[^/]+\/feedback$/)) {
      return await submitFeedback(pathParameters.id, JSON.parse(body || '{}'));
    }

    // Export data
    if (route.match(/^GET \/export$/)) {
      return await exportData(queryStringParameters);
    }

    // Health check
    if (route.match(/^GET \/health$/)) {
      return apiResponse(200, {
        status: 'healthy',
        timestamp: new Date().toISOString()
      });
    }

    // Not found
    return apiResponse(404, { error: 'Not found' });

  } catch (error) {
    logger.error('API error', {
      error: error.message,
      stack: error.stack
    });

    return apiResponse(500, {
      error: 'Internal server error',
      message: error.message
    });
  }
};

/**
 * Get pending approvals
 */
async function getPendingApprovals(params = {}) {
  const userEmail = params?.userEmail || process.env.USER_EMAIL || 'terrance@goodportion.org';
  const limit = parseInt(params?.limit) || 20;
  const type = params?.type;

  let approvals;
  if (type) {
    approvals = await approvalQueue.getPendingByType(type, limit);
  } else {
    approvals = await approvalQueue.getPendingApprovals(userEmail, limit);
  }

  return apiResponse(200, {
    count: approvals.length,
    approvals: approvals.map(formatApproval)
  });
}

/**
 * Get specific approval
 */
async function getApproval(approvalId) {
  const approval = await approvalQueue.getApproval(approvalId);

  if (!approval) {
    return apiResponse(404, { error: 'Approval not found' });
  }

  return apiResponse(200, formatApproval(approval));
}

/**
 * Approve item
 */
async function approveItem(approvalId, body) {
  const { modifications, finalContent, approvedBy } = body;

  const result = await approvalQueue.approve(approvalId, {
    approvedBy: approvedBy || 'api',
    modifications,
    finalContent
  });

  return apiResponse(200, {
    message: 'Approval granted',
    approval: formatApproval(result)
  });
}

/**
 * Reject item
 */
async function rejectItem(approvalId, body) {
  const { reason } = body;

  const result = await approvalQueue.reject(approvalId, reason);

  return apiResponse(200, {
    message: 'Approval rejected',
    approval: formatApproval(result)
  });
}

/**
 * Bulk approve
 */
async function bulkApprove(body) {
  const { approvalIds, approvedBy } = body;

  if (!approvalIds || !Array.isArray(approvalIds)) {
    return apiResponse(400, { error: 'approvalIds array required' });
  }

  const results = await approvalQueue.bulkApprove(
    approvalIds,
    approvedBy || 'api'
  );

  return apiResponse(200, {
    message: 'Bulk approval complete',
    successful: results.successful.length,
    failed: results.failed.length,
    results
  });
}

/**
 * Get statistics
 */
async function getStatistics(params = {}) {
  const userEmail = params?.userEmail || process.env.USER_EMAIL || 'terrance@goodportion.org';

  const stats = await approvalQueue.getStatistics(userEmail);

  return apiResponse(200, stats);
}

/**
 * Get dashboard data
 */
async function getDashboardData(params = {}) {
  const days = parseInt(params?.days) || 7;

  const dashboardData = await emailState.getDashboardData(days);

  // Add pending approvals
  const userEmail = params?.userEmail || process.env.USER_EMAIL || 'terrance@goodportion.org';
  const pendingApprovals = await approvalQueue.getPendingApprovals(userEmail, 10);

  return apiResponse(200, {
    ...dashboardData,
    pendingApprovals: pendingApprovals.map(formatApproval)
  });
}

/**
 * Get email history
 */
async function getEmailHistory(params = {}) {
  const { date, tier, limit } = params;

  let emails;
  if (date) {
    emails = await emailState.getEmailsByDate(date, parseInt(limit) || 100);
  } else if (tier) {
    emails = await emailState.getEmailsByTier(tier, parseInt(limit) || 50);
  } else {
    // Default to today
    emails = await emailState.getEmailsByDate(new Date(), parseInt(limit) || 100);
  }

  return apiResponse(200, {
    count: emails.length,
    emails: emails.map(formatEmail)
  });
}

/**
 * Get specific email
 */
async function getEmail(emailId) {
  const history = await emailState.getEmailHistory(emailId);

  if (!history || history.length === 0) {
    return apiResponse(404, { error: 'Email not found' });
  }

  return apiResponse(200, {
    email: formatEmail(history[0]),
    history: history.map(formatEmail)
  });
}

/**
 * Submit feedback for learning
 */
async function submitFeedback(emailId, body) {
  const {
    feedback,
    originalTier,
    correctTier,
    notes,
    subjectPattern,
    senderPattern,
    keywords
  } = body;

  await emailState.updateLearning(emailId, {
    feedback,
    originalTier,
    correctTier,
    notes,
    subjectPattern,
    senderPattern,
    keywords
  });

  return apiResponse(200, {
    message: 'Feedback recorded',
    emailId
  });
}

/**
 * Export data
 */
async function exportData(params = {}) {
  const userEmail = params?.userEmail || process.env.USER_EMAIL || 'terrance@goodportion.org';

  const data = await approvalQueue.export(userEmail);

  return apiResponse(200, data);
}

/**
 * Format approval for API response
 */
function formatApproval(approval) {
  return {
    id: approval.approvalId,
    type: approval.type,
    status: approval.status,
    email: {
      id: approval.emailId,
      subject: approval.subject,
      from: approval.from,
      to: approval.to,
      threadId: approval.threadId
    },
    action: approval.action,
    actionType: approval.actionType,
    tier: approval.tier,
    draftContent: approval.draftContent,
    suggestedResponse: approval.suggestedResponse,
    confidence: approval.confidence,
    reasoning: approval.reasoning,
    tags: approval.tags,
    createdAt: new Date(approval.timestamp).toISOString(),
    approvedAt: approval.approvedAt ? new Date(approval.approvedAt).toISOString() : null,
    rejectedAt: approval.rejectedAt ? new Date(approval.rejectedAt).toISOString() : null,
    rejectionReason: approval.rejectionReason,
    gmailLink: `https://mail.google.com/mail/u/0/#inbox/${approval.emailId}`
  };
}

/**
 * Format email for API response
 */
function formatEmail(email) {
  return {
    id: email.emailId,
    messageId: email.messageId,
    threadId: email.threadId,
    subject: email.subject,
    from: email.from,
    to: email.to,
    cc: email.cc,
    date: email.date,
    snippet: email.snippet,
    tier: email.tier,
    classification: email.classification,
    action: email.action,
    confidence: email.confidence,
    labels: email.labels,
    tags: email.tags,
    responseGenerated: email.responseGenerated,
    responseSent: email.responseSent,
    agentProcessed: email.agentProcessed,
    processingTime: email.processingTime,
    processedAt: new Date(email.timestamp).toISOString(),
    gmailLink: `https://mail.google.com/mail/u/0/#inbox/${email.emailId}`
  };
}

// Express adapter for local development
if (require.main === module) {
  const express = require('express');
  const app = express();

  app.use(express.json());

  // Convert Express to Lambda-like events
  app.all('*', async (req, res) => {
    const event = {
      httpMethod: req.method,
      path: req.path,
      pathParameters: req.params,
      queryStringParameters: req.query,
      body: JSON.stringify(req.body)
    };

    // Extract path parameters
    const pathMatch = req.path.match(/\/approvals\/([^/]+)/);
    if (pathMatch) {
      event.pathParameters = { id: pathMatch[1] };
    }

    const emailMatch = req.path.match(/\/emails\/([^/]+)/);
    if (emailMatch) {
      event.pathParameters = { id: emailMatch[1] };
    }

    const response = await exports.handler(event, {});

    res.status(response.statusCode);
    Object.entries(response.headers || {}).forEach(([key, value]) => {
      res.set(key, value);
    });
    res.send(response.body);
  });

  const PORT = process.env.PORT || 3001;
  app.listen(PORT, () => {
    console.log(`Approval API running on http://localhost:${PORT}`);
    console.log('\nAvailable endpoints:');
    console.log('  GET  /health                      - Health check');
    console.log('  GET  /approvals                   - List pending approvals');
    console.log('  GET  /approvals/:id               - Get specific approval');
    console.log('  POST /approvals/:id/approve       - Approve item');
    console.log('  POST /approvals/:id/reject        - Reject item');
    console.log('  POST /approvals/bulk-approve      - Bulk approve');
    console.log('  GET  /stats                       - Get statistics');
    console.log('  GET  /dashboard                   - Get dashboard data');
    console.log('  GET  /emails                      - Get email history');
    console.log('  GET  /emails/:id                  - Get specific email');
    console.log('  POST /emails/:id/feedback         - Submit feedback');
    console.log('  GET  /export                      - Export all data');
  });
}