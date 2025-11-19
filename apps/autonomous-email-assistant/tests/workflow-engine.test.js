/**
 * Tests for Workflow Engine
 */

const { WorkflowEngine } = require('../lib/workflow-engine');

describe('WorkflowEngine', () => {
  let engine;

  beforeEach(() => {
    engine = new WorkflowEngine();
  });

  describe('createWorkflow', () => {
    test('creates a workflow with valid definition', () => {
      const definition = {
        name: 'Auto-reply to newsletters',
        trigger: { type: 'email_received' },
        conditions: [
          { type: 'from_contains', values: ['newsletter@'] }
        ],
        actions: [
          { type: 'add_label', parameters: { label: 'Newsletters' } }
        ]
      };

      const workflow = engine.createWorkflow(definition);

      expect(workflow).toBeDefined();
      expect(workflow.id).toBeDefined();
      expect(workflow.name).toBe('Auto-reply to newsletters');
      expect(workflow.enabled).toBe(true);
      expect(workflow.executionCount).toBe(0);
    });

    test('workflow is enabled by default', () => {
      const workflow = engine.createWorkflow({
        name: 'Test',
        trigger: { type: 'email_received' },
        actions: []
      });

      expect(workflow.enabled).toBe(true);
    });

    test('can create disabled workflow', () => {
      const workflow = engine.createWorkflow({
        name: 'Test',
        trigger: { type: 'email_received' },
        actions: [],
        enabled: false
      });

      expect(workflow.enabled).toBe(false);
    });
  });

  describe('updateWorkflow', () => {
    test('updates workflow properties', () => {
      const workflow = engine.createWorkflow({
        name: 'Original Name',
        trigger: { type: 'email_received' },
        actions: []
      });

      const updated = engine.updateWorkflow(workflow.id, {
        name: 'Updated Name',
        enabled: false
      });

      expect(updated.name).toBe('Updated Name');
      expect(updated.enabled).toBe(false);
    });

    test('throws error for non-existent workflow', () => {
      expect(() => {
        engine.updateWorkflow('non-existent-id', { name: 'Test' });
      }).toThrow();
    });
  });

  describe('deleteWorkflow', () => {
    test('deletes existing workflow', () => {
      const workflow = engine.createWorkflow({
        name: 'Test',
        trigger: { type: 'email_received' },
        actions: []
      });

      const deleted = engine.deleteWorkflow(workflow.id);
      expect(deleted).toBe(true);

      const retrieved = engine.getWorkflow(workflow.id);
      expect(retrieved).toBeUndefined();
    });

    test('returns false for non-existent workflow', () => {
      const deleted = engine.deleteWorkflow('non-existent-id');
      expect(deleted).toBe(false);
    });
  });

  describe('evaluateConditions', () => {
    test('returns true when all conditions match', async () => {
      const conditions = [
        { type: 'from_contains', values: ['example.com'] },
        { type: 'subject_contains', values: ['meeting'] }
      ];

      const data = {
        from: 'user@example.com',
        subject: 'Meeting request for next week'
      };

      const result = await engine.evaluateConditions(conditions, data);
      expect(result).toBe(true);
    });

    test('returns false when any condition fails', async () => {
      const conditions = [
        { type: 'from_contains', values: ['example.com'] },
        { type: 'subject_contains', values: ['urgent'] }
      ];

      const data = {
        from: 'user@example.com',
        subject: 'Normal email'
      };

      const result = await engine.evaluateConditions(conditions, data);
      expect(result).toBe(false);
    });

    test('returns true when no conditions specified', async () => {
      const result = await engine.evaluateConditions([], {});
      expect(result).toBe(true);
    });
  });

  describe('executeWorkflow', () => {
    test('executes workflow with matching conditions', async () => {
      const workflow = engine.createWorkflow({
        name: 'Label VIP emails',
        trigger: { type: 'email_received' },
        conditions: [
          { type: 'from_contains', values: ['ceo@'] }
        ],
        actions: [
          { type: 'add_label', parameters: { label: 'VIP' } }
        ]
      });

      const data = {
        from: 'ceo@company.com',
        subject: 'Important matter'
      };

      const result = await engine.executeWorkflow(workflow, data);

      expect(result.status).toBe('completed');
      expect(result.steps).toHaveLength(1);
      expect(result.steps[0].success).toBe(true);
    });

    test('skips workflow when conditions not met', async () => {
      const workflow = engine.createWorkflow({
        name: 'VIP only',
        trigger: { type: 'email_received' },
        conditions: [
          { type: 'from_contains', values: ['vip@'] }
        ],
        actions: [
          { type: 'add_label', parameters: { label: 'VIP' } }
        ]
      });

      const data = {
        from: 'regular@user.com',
        subject: 'Normal email'
      };

      const result = await engine.executeWorkflow(workflow, data);

      expect(result.status).toBe('skipped');
      expect(result.reason).toBe('Conditions not met');
    });

    test('updates workflow execution count', async () => {
      const workflow = engine.createWorkflow({
        name: 'Test',
        trigger: { type: 'email_received' },
        actions: []
      });

      const initialCount = workflow.executionCount;

      await engine.executeWorkflow(workflow, {});

      expect(workflow.executionCount).toBe(initialCount + 1);
      expect(workflow.lastExecuted).toBeDefined();
    });
  });

  describe('executeWorkflows', () => {
    test('executes all matching workflows', async () => {
      engine.createWorkflow({
        name: 'Workflow 1',
        trigger: { type: 'email_received' },
        actions: []
      });

      engine.createWorkflow({
        name: 'Workflow 2',
        trigger: { type: 'email_received' },
        actions: []
      });

      engine.createWorkflow({
        name: 'Different trigger',
        trigger: { type: 'escalation' },
        actions: []
      });

      const results = await engine.executeWorkflows('email_received', {});

      expect(results).toHaveLength(2);
    });

    test('does not execute disabled workflows', async () => {
      engine.createWorkflow({
        name: 'Enabled',
        trigger: { type: 'email_received' },
        actions: []
      });

      engine.createWorkflow({
        name: 'Disabled',
        trigger: { type: 'email_received' },
        actions: [],
        enabled: false
      });

      const results = await engine.executeWorkflows('email_received', {});

      expect(results).toHaveLength(1);
      expect(results[0].workflowId).toBeDefined();
    });
  });

  describe('resolveParameters', () => {
    test('resolves template variables', () => {
      const params = {
        to: '{{email.from}}',
        subject: 'Re: {{email.subject}}',
        static: 'Hello'
      };

      const data = {
        email: {
          from: 'user@example.com',
          subject: 'Question'
        }
      };

      const resolved = engine.resolveParameters(params, data);

      expect(resolved.to).toBe('user@example.com');
      expect(resolved.subject).toBe('Re: Question');
      expect(resolved.static).toBe('Hello');
    });

    test('handles nested data paths', () => {
      const params = {
        value: '{{email.classification.tier}}'
      };

      const data = {
        email: {
          classification: {
            tier: 2
          }
        }
      };

      const resolved = engine.resolveParameters(params, data);

      expect(resolved.value).toBe(2);
    });

    test('returns undefined for missing paths', () => {
      const params = {
        value: '{{email.nonexistent}}'
      };

      const data = {
        email: {
          subject: 'Test'
        }
      };

      const resolved = engine.resolveParameters(params, data);

      expect(resolved.value).toBeUndefined();
    });
  });

  describe('getStatistics', () => {
    test('returns correct workflow statistics', async () => {
      engine.createWorkflow({
        name: 'Test 1',
        trigger: { type: 'email_received' },
        actions: []
      });

      engine.createWorkflow({
        name: 'Test 2',
        trigger: { type: 'email_received' },
        actions: [],
        enabled: false
      });

      // Execute one workflow
      const workflow = engine.getWorkflow(
        engine.listWorkflows()[0].id
      );
      await engine.executeWorkflow(workflow, {});

      const stats = engine.getStatistics();

      expect(stats.totalWorkflows).toBe(2);
      expect(stats.enabledWorkflows).toBe(1);
      expect(stats.totalExecutions).toBeGreaterThanOrEqual(1);
    });
  });

  describe('exportWorkflows', () => {
    test('exports all workflows', () => {
      engine.createWorkflow({
        name: 'Workflow 1',
        trigger: { type: 'email_received' },
        actions: []
      });

      engine.createWorkflow({
        name: 'Workflow 2',
        trigger: { type: 'escalation' },
        actions: []
      });

      const exported = engine.exportWorkflows();

      expect(exported.workflows).toHaveLength(2);
      expect(exported.exportedAt).toBeDefined();
    });
  });

  describe('importWorkflows', () => {
    test('imports workflows from export', () => {
      const data = {
        workflows: [
          {
            name: 'Imported 1',
            trigger: { type: 'email_received' },
            actions: []
          },
          {
            name: 'Imported 2',
            trigger: { type: 'escalation' },
            actions: []
          }
        ]
      };

      const result = engine.importWorkflows(data);

      expect(result.imported).toBe(2);
      expect(engine.listWorkflows()).toHaveLength(2);
    });
  });
});
