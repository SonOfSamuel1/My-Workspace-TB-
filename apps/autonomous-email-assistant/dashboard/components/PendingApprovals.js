/**
 * Pending Approvals Component
 * Displays drafts awaiting approval with action buttons
 */

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
  CheckCircleIcon,
  XCircleIcon,
  PencilIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

const priorityColors = {
  high: 'border-red-300 bg-red-50',
  normal: 'border-blue-300 bg-blue-50',
  low: 'border-gray-300 bg-gray-50'
};

export default function PendingApprovals({ approvals }) {
  const [expandedId, setExpandedId] = useState(null);

  const handleApprove = async (id) => {
    // In production, call API to approve
    console.log('Approving draft:', id);
  };

  const handleReject = async (id) => {
    // In production, call API to reject
    console.log('Rejecting draft:', id);
  };

  const handleEdit = (id) => {
    // In production, open edit modal
    console.log('Editing draft:', id);
  };

  if (!approvals || approvals.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <ClockIcon className="h-5 w-5 mr-2 text-yellow-600" />
          Pending Approvals ({approvals.length})
        </h2>
        <span className="text-sm text-gray-500">
          Review and approve draft responses
        </span>
      </div>

      <div className="divide-y divide-gray-200">
        {approvals.map((approval) => (
          <div
            key={approval.id}
            className={`p-6 border-l-4 ${priorityColors[approval.priority]}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-900">
                    To: {approval.to}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    approval.priority === 'high'
                      ? 'bg-red-100 text-red-800'
                      : approval.priority === 'normal'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {approval.priority} priority
                  </span>
                </div>

                <p className="mt-1 text-sm font-semibold text-gray-900">
                  {approval.subject}
                </p>

                <p className="mt-2 text-sm text-gray-500">
                  Created {formatDistanceToNow(new Date(approval.createdAt), { addSuffix: true })}
                </p>

                {expandedId === approval.id ? (
                  <div className="mt-4 p-4 bg-white rounded border border-gray-200">
                    <p className="text-sm text-gray-700 whitespace-pre-line">
                      {approval.draft}
                    </p>
                  </div>
                ) : (
                  <div className="mt-2">
                    <p className="text-sm text-gray-700 line-clamp-2">
                      {approval.draft}
                    </p>
                    <button
                      onClick={() => setExpandedId(approval.id)}
                      className="mt-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                    >
                      Show full draft →
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 flex items-center space-x-3">
              <button
                onClick={() => handleApprove(approval.id)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                <CheckCircleIcon className="h-5 w-5 mr-2" />
                Approve & Send
              </button>

              <button
                onClick={() => handleEdit(approval.id)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <PencilIcon className="h-5 w-5 mr-2" />
                Edit
              </button>

              <button
                onClick={() => handleReject(approval.id)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <XCircleIcon className="h-5 w-5 mr-2" />
                Reject
              </button>

              {expandedId === approval.id && (
                <button
                  onClick={() => setExpandedId(null)}
                  className="text-sm text-gray-600 hover:text-gray-700"
                >
                  Collapse
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
