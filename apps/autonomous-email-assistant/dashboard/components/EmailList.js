/**
 * Email List Component
 * Displays list of recent emails with status
 */

import { formatDistanceToNow } from 'date-fns';
import {
  EnvelopeIcon,
  PaperClipIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  FlagIcon
} from '@heroicons/react/24/outline';

const tierColors = {
  1: 'bg-red-100 text-red-800',
  2: 'bg-green-100 text-green-800',
  3: 'bg-blue-100 text-blue-800',
  4: 'bg-gray-100 text-gray-800'
};

const tierLabels = {
  1: 'Tier 1 - Escalated',
  2: 'Tier 2 - Handled',
  3: 'Tier 3 - Draft',
  4: 'Tier 4 - Flagged'
};

const actionIcons = {
  'handled': CheckCircleIcon,
  'draft_created': ClockIcon,
  'escalated': ExclamationTriangleIcon,
  'flagged': FlagIcon
};

export default function EmailList({ emails }) {
  if (!emails || emails.length === 0) {
    return (
      <div className="p-8 text-center text-gray-500">
        <EnvelopeIcon className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2">No emails to display</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-200">
      {emails.map((email) => {
        const ActionIcon = actionIcons[email.action] || EnvelopeIcon;

        return (
          <div
            key={email.id}
            className="p-4 hover:bg-gray-50 transition-colors cursor-pointer"
          >
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0">
                <ActionIcon
                  className={`h-6 w-6 ${
                    email.action === 'escalated'
                      ? 'text-red-600'
                      : email.action === 'handled'
                      ? 'text-green-600'
                      : 'text-blue-600'
                  }`}
                />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {email.from}
                  </p>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${tierColors[email.tier]}`}>
                    {tierLabels[email.tier]}
                  </span>
                </div>

                <p className="text-sm text-gray-900 font-medium mt-1">
                  {email.subject}
                </p>

                <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                  <span>
                    {formatDistanceToNow(new Date(email.date), { addSuffix: true })}
                  </span>

                  {email.hasAttachments && (
                    <span className="flex items-center">
                      <PaperClipIcon className="h-4 w-4 mr-1" />
                      Attachments
                    </span>
                  )}

                  {email.sentiment && (
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      email.sentiment.urgency === 'high'
                        ? 'bg-red-100 text-red-700'
                        : email.sentiment.urgency === 'medium'
                        ? 'bg-yellow-100 text-yellow-700'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {email.sentiment.urgency} urgency
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
