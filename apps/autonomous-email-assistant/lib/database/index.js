/**
 * Database Module Index
 * Exports all database-related functionality
 */

const ApprovalQueueManager = require('./approval-queue');
const EmailStateManager = require('./email-state');

// Singleton instances for convenience
let approvalQueueInstance = null;
let emailStateInstance = null;

/**
 * Get or create ApprovalQueueManager instance
 */
function getApprovalQueue(config = {}) {
  if (!approvalQueueInstance) {
    approvalQueueInstance = new ApprovalQueueManager(config);
  }
  return approvalQueueInstance;
}

/**
 * Get or create EmailStateManager instance
 */
function getEmailState(config = {}) {
  if (!emailStateInstance) {
    emailStateInstance = new EmailStateManager(config);
  }
  return emailStateInstance;
}

/**
 * Initialize all database connections
 */
async function initializeDatabase(config = {}) {
  const approvalQueue = getApprovalQueue(config);
  const emailState = getEmailState(config);

  return {
    approvalQueue,
    emailState,
    initialized: true
  };
}

/**
 * Reset singleton instances (for testing)
 */
function resetInstances() {
  approvalQueueInstance = null;
  emailStateInstance = null;
}

module.exports = {
  ApprovalQueueManager,
  EmailStateManager,
  getApprovalQueue,
  getEmailState,
  initializeDatabase,
  resetInstances
};