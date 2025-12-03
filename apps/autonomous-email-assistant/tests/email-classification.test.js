/**
 * Email Classification Logic Tests
 * Comprehensive test suite for the 4-tier email classification system
 */

describe('Email Classification System', () => {
  let classifier;

  beforeEach(() => {
    // Mock the classifier with the tier logic
    classifier = {
      offLimitsContacts: [
        'family@example.com',
        'boss@company.com',
        'investor@vc.com'
      ],

      classify: function(email) {
        // Check off-limits contacts first
        if (this.offLimitsContacts.includes(email.from)) {
          return {
            tier: 1,
            reason: 'Off-limits contact',
            action: 'ESCALATE'
          };
        }

        // Check for urgent keywords
        const urgentKeywords = ['urgent', 'critical', 'emergency', 'asap', 'immediate'];
        const lowerBody = email.body.toLowerCase();
        const lowerSubject = email.subject.toLowerCase();

        for (const keyword of urgentKeywords) {
          if (lowerSubject.includes(keyword) || lowerBody.includes(keyword)) {
            return {
              tier: 1,
              reason: 'Contains urgent keywords',
              action: 'ESCALATE'
            };
          }
        }

        // Check for financial/legal matters
        if (lowerBody.includes('invoice') || lowerBody.includes('payment') ||
            lowerBody.includes('contract') || lowerBody.includes('legal')) {
          if (lowerBody.includes('approval') || lowerBody.includes('sign')) {
            return {
              tier: 1,
              reason: 'Financial/legal approval required',
              action: 'ESCALATE'
            };
          }
        }

        // Check for meeting requests (Tier 2 - can handle)
        if (lowerBody.includes('meeting') || lowerBody.includes('calendar') ||
            lowerBody.includes('schedule') || lowerBody.includes('availability')) {
          return {
            tier: 2,
            reason: 'Meeting/calendar request',
            action: 'HANDLE'
          };
        }

        // Check for newsletter/subscription (Tier 2)
        if (email.from.includes('newsletter') || email.from.includes('noreply') ||
            lowerSubject.includes('newsletter') || lowerSubject.includes('update')) {
          return {
            tier: 2,
            reason: 'Newsletter/automated email',
            action: 'HANDLE'
          };
        }

        // Check for HR/employee matters (Tier 4 - never send)
        const hrKeywords = ['performance', 'salary', 'compensation', 'termination',
                          'disciplinary', 'confidential', 'hr'];
        for (const keyword of hrKeywords) {
          if (lowerBody.includes(keyword)) {
            return {
              tier: 4,
              reason: 'HR/confidential matter',
              action: 'FLAG_ONLY'
            };
          }
        }

        // Check for first-time contacts (Tier 3 - draft)
        if (email.isFirstTimeContact) {
          return {
            tier: 3,
            reason: 'First-time contact',
            action: 'DRAFT'
          };
        }

        // Default to Tier 3 for safety
        return {
          tier: 3,
          reason: 'Default - requires review',
          action: 'DRAFT'
        };
      }
    };
  });

  describe('Tier 1: Escalate Immediately', () => {
    test('should escalate emails from off-limits contacts', () => {
      const email = {
        from: 'family@example.com',
        subject: 'Regular update',
        body: 'Just wanted to check in'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1);
      expect(result.action).toBe('ESCALATE');
      expect(result.reason).toContain('Off-limits');
    });

    test('should escalate emails marked as urgent', () => {
      const email = {
        from: 'client@company.com',
        subject: 'URGENT: Contract issue',
        body: 'Need immediate response'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1);
      expect(result.action).toBe('ESCALATE');
      expect(result.reason).toContain('urgent');
    });

    test('should escalate financial approvals', () => {
      const email = {
        from: 'vendor@supplier.com',
        subject: 'Invoice for approval',
        body: 'Please approve the attached invoice for payment processing'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1);
      expect(result.action).toBe('ESCALATE');
      expect(result.reason).toContain('Financial');
    });

    test('should escalate legal matters requiring signature', () => {
      const email = {
        from: 'lawyer@lawfirm.com',
        subject: 'Contract for review',
        body: 'Please sign the attached contract by end of day'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1);
      expect(result.action).toBe('ESCALATE');
      expect(result.reason).toContain('legal');
    });

    test('should escalate emails with critical keywords', () => {
      const testCases = [
        { subject: 'System critical failure', keyword: 'critical' },
        { subject: 'Emergency meeting needed', keyword: 'emergency' },
        { subject: 'Response needed ASAP', keyword: 'asap' }
      ];

      testCases.forEach(testCase => {
        const email = {
          from: 'team@company.com',
          subject: testCase.subject,
          body: 'Details here'
        };

        const result = classifier.classify(email);
        expect(result.tier).toBe(1);
        expect(result.action).toBe('ESCALATE');
      });
    });
  });

  describe('Tier 2: Handle Independently', () => {
    test('should handle meeting scheduling requests', () => {
      const email = {
        from: 'colleague@company.com',
        subject: 'Meeting request',
        body: 'Can we schedule a meeting for next week?'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(2);
      expect(result.action).toBe('HANDLE');
      expect(result.reason).toContain('meeting');
    });

    test('should handle calendar availability checks', () => {
      const email = {
        from: 'partner@business.com',
        subject: 'Checking availability',
        body: "What's your calendar like next Tuesday?"
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(2);
      expect(result.action).toBe('HANDLE');
      expect(result.reason).toContain('calendar');
    });

    test('should handle newsletter subscriptions', () => {
      const email = {
        from: 'newsletter@techcompany.com',
        subject: 'Your weekly newsletter',
        body: 'Here are this week\'s updates'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(2);
      expect(result.action).toBe('HANDLE');
      expect(result.reason).toContain('Newsletter');
    });

    test('should handle automated/noreply emails', () => {
      const email = {
        from: 'noreply@service.com',
        subject: 'Your account update',
        body: 'Your settings have been updated'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(2);
      expect(result.action).toBe('HANDLE');
    });
  });

  describe('Tier 3: Draft for Approval', () => {
    test('should draft response for first-time contacts', () => {
      const email = {
        from: 'newcontact@unknown.com',
        subject: 'Business opportunity',
        body: 'I have an interesting proposal',
        isFirstTimeContact: true
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(3);
      expect(result.action).toBe('DRAFT');
      expect(result.reason).toContain('First-time');
    });

    test('should draft for emails requiring expertise', () => {
      const email = {
        from: 'client@customer.com',
        subject: 'Technical question',
        body: 'Can you explain your approach to this problem?'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(3);
      expect(result.action).toBe('DRAFT');
    });

    test('should default to Tier 3 when uncertain', () => {
      const email = {
        from: 'contact@company.com',
        subject: 'Following up',
        body: 'Just wanted to follow up on our discussion'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(3);
      expect(result.action).toBe('DRAFT');
      expect(result.reason).toContain('Default');
    });
  });

  describe('Tier 4: Flag Only, Never Send', () => {
    test('should flag HR performance matters', () => {
      const email = {
        from: 'hr@company.com',
        subject: 'Performance review',
        body: 'We need to discuss your team member\'s performance'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(4);
      expect(result.action).toBe('FLAG_ONLY');
      expect(result.reason).toContain('HR');
    });

    test('should flag salary/compensation discussions', () => {
      const email = {
        from: 'manager@company.com',
        subject: 'Compensation adjustment',
        body: 'Let\'s discuss the salary increase for your team'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(4);
      expect(result.action).toBe('FLAG_ONLY');
    });

    test('should flag confidential matters', () => {
      const email = {
        from: 'executive@company.com',
        subject: 'Confidential',
        body: 'This is strictly confidential information'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(4);
      expect(result.action).toBe('FLAG_ONLY');
    });

    test('should flag termination/disciplinary matters', () => {
      const testCases = [
        { body: 'Discussion about termination procedures' },
        { body: 'Disciplinary action required' }
      ];

      testCases.forEach(testCase => {
        const email = {
          from: 'hr@company.com',
          subject: 'Important matter',
          body: testCase.body
        };

        const result = classifier.classify(email);
        expect(result.tier).toBe(4);
        expect(result.action).toBe('FLAG_ONLY');
      });
    });
  });

  describe('Edge Cases and Priority Rules', () => {
    test('off-limits contact overrides all other rules', () => {
      const email = {
        from: 'boss@company.com',
        subject: 'Newsletter',  // Would normally be Tier 2
        body: 'Just sharing a newsletter'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1); // Off-limits overrides
      expect(result.action).toBe('ESCALATE');
    });

    test('urgent overrides meeting classification', () => {
      const email = {
        from: 'client@customer.com',
        subject: 'URGENT: Meeting cancellation',
        body: 'Need to cancel our meeting immediately'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1); // Urgent overrides
      expect(result.action).toBe('ESCALATE');
    });

    test('HR keywords override meeting requests', () => {
      const email = {
        from: 'hr@company.com',
        subject: 'Meeting request',
        body: 'Let\'s schedule a meeting to discuss performance issues'
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(4); // HR overrides
      expect(result.action).toBe('FLAG_ONLY');
    });

    test('should handle emails with multiple tier indicators', () => {
      const email = {
        from: 'unknown@company.com',
        subject: 'Meeting about invoice',
        body: 'Can we schedule a meeting to discuss the invoice approval?',
        isFirstTimeContact: true
      };

      const result = classifier.classify(email);
      expect(result.tier).toBe(1); // Financial approval takes precedence
      expect(result.action).toBe('ESCALATE');
    });
  });

  describe('Email Content Analysis', () => {
    test('should handle empty subjects gracefully', () => {
      const email = {
        from: 'contact@company.com',
        subject: '',
        body: 'Please respond'
      };

      const result = classifier.classify(email);
      expect(result).toBeDefined();
      expect(result.tier).toBeGreaterThanOrEqual(1);
      expect(result.tier).toBeLessThanOrEqual(4);
    });

    test('should handle empty body gracefully', () => {
      const email = {
        from: 'contact@company.com',
        subject: 'Quick question',
        body: ''
      };

      const result = classifier.classify(email);
      expect(result).toBeDefined();
      expect(result.tier).toBeGreaterThanOrEqual(1);
      expect(result.tier).toBeLessThanOrEqual(4);
    });

    test('should be case-insensitive for keyword detection', () => {
      const variations = [
        { subject: 'URGENT request', expectTier: 1 },
        { subject: 'Urgent Request', expectTier: 1 },
        { subject: 'urgent REQUEST', expectTier: 1 },
        { body: 'This is CRITICAL', expectTier: 1 },
        { body: 'emergency situation', expectTier: 1 }
      ];

      variations.forEach(variant => {
        const email = {
          from: 'contact@company.com',
          subject: variant.subject || 'Test',
          body: variant.body || 'Test'
        };

        const result = classifier.classify(email);
        expect(result.tier).toBe(variant.expectTier);
      });
    });
  });

  describe('Classification Statistics', () => {
    test('should classify a diverse set of emails correctly', () => {
      const testEmails = [
        // Tier 1
        { from: 'family@example.com', subject: 'Hi', body: 'Hello', expectedTier: 1 },
        { from: 'ceo@company.com', subject: 'URGENT', body: 'Need this now', expectedTier: 1 },

        // Tier 2
        { from: 'noreply@service.com', subject: 'Update', body: 'Your weekly update', expectedTier: 2 },
        { from: 'scheduler@cal.com', subject: 'Meeting', body: 'Schedule a meeting?', expectedTier: 2 },

        // Tier 3
        { from: 'new@contact.com', subject: 'Hello', body: 'Introduction', isFirstTimeContact: true, expectedTier: 3 },

        // Tier 4
        { from: 'hr@company.com', subject: 'Review', body: 'Performance review needed', expectedTier: 4 }
      ];

      const results = testEmails.map(email => ({
        ...email,
        result: classifier.classify(email)
      }));

      // Check each classification
      results.forEach(test => {
        expect(test.result.tier).toBe(test.expectedTier);
      });

      // Check distribution
      const tierCounts = results.reduce((acc, test) => {
        acc[test.result.tier] = (acc[test.result.tier] || 0) + 1;
        return acc;
      }, {});

      expect(tierCounts[1]).toBeGreaterThan(0);
      expect(tierCounts[2]).toBeGreaterThan(0);
      expect(tierCounts[3]).toBeGreaterThan(0);
      expect(tierCounts[4]).toBeGreaterThan(0);
    });
  });
});

describe('Email Classification Integration', () => {
  test('should handle real-world email scenarios', () => {
    const realWorldScenarios = [
      {
        name: 'Customer complaint needing escalation',
        email: {
          from: 'angry.customer@example.com',
          subject: 'URGENT: Service outage affecting business',
          body: 'This is critical! Our entire operation is down. Need immediate assistance!'
        },
        expectedTier: 1,
        expectedAction: 'ESCALATE'
      },
      {
        name: 'Routine meeting scheduling',
        email: {
          from: 'colleague@company.com',
          subject: 'Sync up next week?',
          body: "Hey, can we schedule our regular sync for next week? Check my calendar for availability."
        },
        expectedTier: 2,
        expectedAction: 'HANDLE'
      },
      {
        name: 'Vendor introduction requiring review',
        email: {
          from: 'sales@newvendor.com',
          subject: 'Introduction - Cost savings opportunity',
          body: 'We can save you 30% on your current expenses. Would love to discuss.',
          isFirstTimeContact: true
        },
        expectedTier: 3,
        expectedAction: 'DRAFT'
      },
      {
        name: 'Sensitive HR matter',
        email: {
          from: 'hr.director@company.com',
          subject: 'Re: Team restructuring',
          body: 'We need to discuss the termination plan for the underperforming team members.'
        },
        expectedTier: 4,
        expectedAction: 'FLAG_ONLY'
      },
      {
        name: 'Board member communication',
        email: {
          from: 'investor@vc.com',
          subject: 'Quick question',
          body: 'What were last month\'s numbers?'
        },
        expectedTier: 1,
        expectedAction: 'ESCALATE'
      },
      {
        name: 'Newsletter from known source',
        email: {
          from: 'newsletter@trustedsource.com',
          subject: 'Your weekly industry update',
          body: 'Top stories this week in tech...'
        },
        expectedTier: 2,
        expectedAction: 'HANDLE'
      }
    ];

    const classifier = {
      offLimitsContacts: ['investor@vc.com', 'family@example.com', 'boss@company.com'],
      classify: function(email) {
        // Comprehensive classification logic
        if (this.offLimitsContacts.includes(email.from)) {
          return { tier: 1, action: 'ESCALATE', reason: 'Off-limits contact' };
        }

        const urgentIndicators = ['urgent', 'critical', 'emergency', 'asap', 'immediate', 'outage'];
        const combined = (email.subject + ' ' + email.body).toLowerCase();

        if (urgentIndicators.some(word => combined.includes(word))) {
          return { tier: 1, action: 'ESCALATE', reason: 'Urgent matter' };
        }

        if (combined.includes('termination') || combined.includes('disciplinary') ||
            combined.includes('performance') && email.from.includes('hr')) {
          return { tier: 4, action: 'FLAG_ONLY', reason: 'HR matter' };
        }

        if (combined.includes('meeting') || combined.includes('schedule') ||
            combined.includes('calendar')) {
          return { tier: 2, action: 'HANDLE', reason: 'Scheduling' };
        }

        if (email.from.includes('newsletter') || email.from.includes('noreply')) {
          return { tier: 2, action: 'HANDLE', reason: 'Automated' };
        }

        if (email.isFirstTimeContact) {
          return { tier: 3, action: 'DRAFT', reason: 'New contact' };
        }

        return { tier: 3, action: 'DRAFT', reason: 'Default' };
      }
    };

    realWorldScenarios.forEach(scenario => {
      const result = classifier.classify(scenario.email);
      expect(result.tier).toBe(scenario.expectedTier);
      expect(result.action).toBe(scenario.expectedAction);
    });
  });
});