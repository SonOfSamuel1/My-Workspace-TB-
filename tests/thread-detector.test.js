/**
 * Tests for Thread Detector
 */

const { ThreadDetector } = require('../lib/thread-detector');

describe('ThreadDetector', () => {
  let detector;

  beforeEach(() => {
    detector = new ThreadDetector();
  });

  describe('detectThread', () => {
    test('detects thread by In-Reply-To header', () => {
      const email1 = {
        id: 'email1',
        messageId: 'msg1@example.com',
        subject: 'Meeting Request',
        from: 'john@example.com',
        to: 'jane@example.com',
        date: new Date('2024-01-01T10:00:00Z')
      };

      const email2 = {
        id: 'email2',
        messageId: 'msg2@example.com',
        inReplyTo: 'msg1@example.com',
        subject: 'Re: Meeting Request',
        from: 'jane@example.com',
        to: 'john@example.com',
        date: new Date('2024-01-01T11:00:00Z')
      };

      const threadId1 = detector.detectThread(email1);
      const threadId2 = detector.detectThread(email2);

      expect(threadId2).toBe(threadId1);
    });

    test('detects thread by similar subject', () => {
      const email1 = {
        id: 'email1',
        subject: 'Project Update',
        from: 'alice@example.com',
        to: 'bob@example.com',
        date: new Date('2024-01-01T10:00:00Z')
      };

      const email2 = {
        id: 'email2',
        subject: 'Re: Project Update',
        from: 'bob@example.com',
        to: 'alice@example.com',
        date: new Date('2024-01-01T11:00:00Z')
      };

      const threadId1 = detector.detectThread(email1);
      const threadId2 = detector.detectThread(email2);

      expect(threadId2).toBe(threadId1);
    });

    test('creates separate threads for different subjects', () => {
      const email1 = {
        id: 'email1',
        subject: 'Meeting A',
        from: 'user1@example.com',
        to: 'user2@example.com',
        date: new Date()
      };

      const email2 = {
        id: 'email2',
        subject: 'Meeting B',
        from: 'user1@example.com',
        to: 'user2@example.com',
        date: new Date()
      };

      const threadId1 = detector.detectThread(email1);
      const threadId2 = detector.detectThread(email2);

      expect(threadId1).not.toBe(threadId2);
    });
  });

  describe('getThread', () => {
    test('returns thread with correct details', () => {
      const email = {
        id: 'email1',
        subject: 'Test Thread',
        from: 'sender@example.com',
        to: 'receiver@example.com',
        date: new Date()
      };

      const threadId = detector.detectThread(email);
      const thread = detector.getThread(threadId);

      expect(thread).toBeDefined();
      expect(thread.subject).toBe('Test Thread');
      expect(thread.emailCount).toBe(1);
      expect(thread.participants).toContain('sender@example.com');
      expect(thread.participants).toContain('receiver@example.com');
    });

    test('updates thread with new emails', () => {
      const email1 = {
        id: 'email1',
        messageId: 'msg1',
        subject: 'Discussion',
        from: 'a@example.com',
        to: 'b@example.com',
        date: new Date('2024-01-01T10:00:00Z')
      };

      const email2 = {
        id: 'email2',
        inReplyTo: 'msg1',
        subject: 'Re: Discussion',
        from: 'b@example.com',
        to: 'a@example.com',
        date: new Date('2024-01-01T11:00:00Z')
      };

      detector.detectThread(email1);
      const threadId = detector.detectThread(email2);
      const thread = detector.getThread(threadId);

      expect(thread.emailCount).toBe(2);
      expect(thread.emails).toHaveLength(2);
    });
  });

  describe('getActiveThreads', () => {
    test('returns most recent threads', () => {
      // Create multiple threads
      for (let i = 0; i < 5; i++) {
        detector.detectThread({
          id: `email${i}`,
          subject: `Thread ${i}`,
          from: 'user@example.com',
          to: 'other@example.com',
          date: new Date(Date.now() - i * 1000 * 60 * 60) // Hours ago
        });
      }

      const activeThreads = detector.getActiveThreads(3);
      expect(activeThreads).toHaveLength(3);
      // Most recent should be first
      expect(activeThreads[0].subject).toBe('Thread 0');
    });
  });

  describe('isFollowUp', () => {
    test('detects follow-up emails', () => {
      const email1 = {
        id: 'email1',
        messageId: 'msg1',
        subject: 'Question',
        from: 'asker@example.com',
        to: 'responder@example.com',
        date: new Date('2024-01-01T10:00:00Z')
      };

      const threadId = detector.detectThread(email1);

      const email2 = {
        id: 'email2',
        inReplyTo: 'msg1',
        subject: 'Re: Question',
        from: 'asker@example.com',
        to: 'responder@example.com',
        date: new Date('2024-01-04T10:00:00Z') // 3 days later
      };

      detector.detectThread(email2);

      const isFollowUp = detector.isFollowUp(email2, threadId);
      expect(isFollowUp).toBe(true);
    });
  });

  describe('getStatistics', () => {
    test('returns correct statistics', () => {
      detector.detectThread({
        id: 'email1',
        subject: 'Thread 1',
        from: 'user@example.com',
        to: 'other@example.com',
        date: new Date()
      });

      detector.detectThread({
        id: 'email2',
        subject: 'Thread 2',
        from: 'user@example.com',
        to: 'other@example.com',
        date: new Date()
      });

      const stats = detector.getStatistics();

      expect(stats.totalThreads).toBe(2);
      expect(stats.totalEmails).toBe(2);
      expect(stats.avgThreadLength).toBe(1);
    });
  });
});
