/**
 * Email Agent Tools Test Suite
 * Tests for Playwright, Calendar, and Data tools
 */

const playwrightTool = require('../lib/tools/playwright-tool');
const calendarTool = require('../lib/tools/calendar-tool');
const dataTool = require('../lib/tools/data-tool');

// Mock googleapis
jest.mock('googleapis', () => ({
  google: {
    auth: {
      OAuth2: jest.fn().mockImplementation(() => ({
        setCredentials: jest.fn()
      }))
    },
    calendar: jest.fn().mockImplementation(() => ({
      events: {
        insert: jest.fn().mockResolvedValue({
          data: {
            id: 'event123',
            summary: 'Test Event',
            htmlLink: 'https://calendar.google.com/event/123'
          }
        }),
        list: jest.fn().mockResolvedValue({
          data: {
            items: []
          }
        }),
        delete: jest.fn().mockResolvedValue({}),
        get: jest.fn().mockResolvedValue({
          data: {
            id: 'event123',
            summary: 'Existing Event'
          }
        }),
        update: jest.fn().mockResolvedValue({
          data: {
            id: 'event123',
            summary: 'Updated Event'
          }
        })
      },
      freebusy: {
        query: jest.fn().mockResolvedValue({
          data: {
            calendars: {
              primary: {
                busy: []
              }
            }
          }
        })
      }
    }))
  }
}));

// Mock playwright
jest.mock('playwright', () => ({
  chromium: {
    launch: jest.fn().mockResolvedValue({
      newContext: jest.fn().mockResolvedValue({
        newPage: jest.fn().mockResolvedValue({
          goto: jest.fn(),
          click: jest.fn(),
          fill: jest.fn(),
          screenshot: jest.fn().mockResolvedValue(Buffer.from('screenshot')),
          title: jest.fn().mockResolvedValue('Page Title'),
          url: jest.fn().mockReturnValue('https://example.com'),
          $$: jest.fn().mockResolvedValue([]),
          evaluate: jest.fn(),
          waitForSelector: jest.fn(),
          waitForLoadState: jest.fn(),
          waitForTimeout: jest.fn(),
          content: jest.fn().mockResolvedValue('<html></html>')
        })
      }),
      close: jest.fn()
    })
  }
}));

// Mock fs.promises
jest.mock('fs', () => ({
  promises: {
    access: jest.fn().mockRejectedValue(new Error('File not found')),
    readFile: jest.fn()
  }
}));

describe('Playwright Tool', () => {
  describe('Initialization', () => {
    test('should initialize with correct properties', () => {
      expect(playwrightTool.name).toBe('playwright');
      expect(playwrightTool.description).toBe('Web automation tool for autonomous browser actions');
      expect(playwrightTool.actions).toBeDefined();
    });

    test('should have all required actions', () => {
      const actions = playwrightTool.getActions();
      const actionNames = actions.map(a => a.name);

      expect(actionNames).toContain('navigate');
      expect(actionNames).toContain('click');
      expect(actionNames).toContain('fill');
      expect(actionNames).toContain('extract');
      expect(actionNames).toContain('screenshot');
      expect(actionNames).toContain('wait');
      expect(actionNames).toContain('scroll');
      expect(actionNames).toContain('submit');
    });
  });

  describe('Action Execution', () => {
    test('should navigate to URL', async () => {
      const result = await playwrightTool.execute({
        action: 'navigate',
        url: 'https://example.com'
      });

      expect(result.success).toBe(true);
      expect(result.action).toBe('navigate');
      expect(result.result.url).toBe('https://example.com');
      expect(result.result.title).toBeDefined();
    });

    test('should click element', async () => {
      const result = await playwrightTool.execute({
        action: 'click',
        selector: '#button'
      });

      expect(result.success).toBe(true);
      expect(result.action).toBe('click');
      expect(result.result.clicked).toBe('#button');
    });

    test('should fill form field', async () => {
      const result = await playwrightTool.execute({
        action: 'fill',
        selector: '#input',
        value: 'test value'
      });

      expect(result.success).toBe(true);
      expect(result.action).toBe('fill');
      expect(result.result.filled).toBe('#input');
      expect(result.result.value).toBe('test value');
    });

    test('should take screenshot', async () => {
      const result = await playwrightTool.execute({
        action: 'screenshot',
        filename: 'test.png'
      });

      expect(result.success).toBe(true);
      expect(result.action).toBe('screenshot');
      expect(result.result.filename).toBe('test.png');
    });

    test('should handle unknown action', async () => {
      const result = await playwrightTool.execute({
        action: 'unknown_action'
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Unknown Playwright action');
    });

    test('should handle action errors gracefully', async () => {
      // Force an error by not providing required parameters
      const result = await playwrightTool.execute({
        action: 'fill',
        selector: '#input'
        // Missing 'value' parameter
      });

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe('Browser Management', () => {
    test('should launch browser on first action', async () => {
      const newTool = new playwrightTool.PlaywrightTool();
      expect(newTool.browser).toBeNull();

      await newTool.execute({
        action: 'navigate',
        url: 'https://example.com'
      });

      expect(newTool.browser).toBeDefined();
    });

    test('should close browser properly', async () => {
      const newTool = new playwrightTool.PlaywrightTool();
      await newTool.ensureBrowser();
      expect(newTool.browser).toBeDefined();

      await newTool.close();
      expect(newTool.browser).toBeNull();
    });
  });
});

describe('Calendar Tool', () => {
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
  });

  describe('Initialization', () => {
    test('should initialize with correct properties', () => {
      expect(calendarTool.name).toBe('calendar');
      expect(calendarTool.description).toBe('Calendar management and scheduling');
    });
  });

  describe('Event Creation', () => {
    test('should create calendar event', async () => {
      const result = await calendarTool.execute({
        action: 'create_event',
        title: 'Test Meeting',
        start: '2024-01-01T10:00:00Z',
        end: '2024-01-01T11:00:00Z',
        attendees: ['user@example.com']
      });

      expect(result.success).toBe(true);
      expect(result.title).toBeDefined();
      expect(result.eventId).toBeDefined();
    });

    test('should handle create event in mock mode', async () => {
      // Calendar tool should work in mock mode when no credentials
      const result = await calendarTool.execute({
        action: 'create_event',
        title: 'Mock Meeting',
        start: '2024-01-01T10:00:00Z',
        end: '2024-01-01T11:00:00Z'
      });

      expect(result.success).toBe(true);
      expect(result.summary).toContain('mock mode');
    });
  });

  describe('Availability Checking', () => {
    test('should check availability', async () => {
      const result = await calendarTool.execute({
        action: 'check_availability',
        start: '2024-01-01T10:00:00Z',
        end: '2024-01-01T11:00:00Z'
      });

      expect(result.available).toBeDefined();
      expect(result.conflicts).toBeDefined();
      expect(result.suggestedTimes).toBeDefined();
    });

    test('should find available time slots', async () => {
      const result = await calendarTool.execute({
        action: 'find_time',
        duration: 60,
        earliestStart: '2024-01-01T09:00:00Z',
        latestEnd: '2024-01-07T17:00:00Z'
      });

      expect(result.found).toBeDefined();
      expect(result.suggestions).toBeDefined();
    });
  });

  describe('Event Management', () => {
    test('should list events', async () => {
      const result = await calendarTool.execute({
        action: 'list_events',
        startDate: '2024-01-01T00:00:00Z',
        maxResults: 10
      });

      expect(result.events).toBeDefined();
      expect(result.count).toBeDefined();
    });

    test('should cancel event', async () => {
      const result = await calendarTool.execute({
        action: 'cancel_event',
        eventId: 'event123'
      });

      expect(result.success).toBe(true);
      expect(result.eventId).toBe('event123');
    });

    test('should update event', async () => {
      const result = await calendarTool.execute({
        action: 'update_event',
        eventId: 'event123',
        updates: {
          summary: 'Updated Title'
        }
      });

      expect(result.success).toBe(true);
      expect(result.eventId).toBe('event123');
    });
  });

  describe('Error Handling', () => {
    test('should handle unknown action', async () => {
      await expect(calendarTool.execute({
        action: 'unknown_action'
      })).rejects.toThrow('Unknown calendar action');
    });
  });
});

describe('Data Tool', () => {
  describe('Text Analysis', () => {
    test('should analyze text', async () => {
      const result = await dataTool.execute({
        action: 'analyze_text',
        text: 'This is a test sentence. It has two sentences.',
        detailed: true
      });

      expect(result.wordCount).toBe(9);
      expect(result.sentences).toBe(2);
      expect(result.hasQuestions).toBe(false);
      expect(result.summary).toContain('9 words');
    });

    test('should perform basic text analysis', async () => {
      const result = await dataTool.execute({
        action: 'analyze_text',
        text: 'Quick test'
      });

      expect(result.wordCount).toBe(2);
      expect(result.topWords).toBeUndefined(); // Not in basic analysis
    });
  });

  describe('Data Extraction', () => {
    test('should extract emails from text', async () => {
      const result = await dataTool.execute({
        action: 'extract_data',
        text: 'Contact us at test@example.com or admin@site.org',
        patterns: ['emails']
      });

      expect(result.extracted.emails).toContain('test@example.com');
      expect(result.extracted.emails).toContain('admin@site.org');
      expect(result.counts.emails).toBe(2);
    });

    test('should extract phone numbers', async () => {
      const result = await dataTool.execute({
        action: 'extract_data',
        text: 'Call us at 555-123-4567 or (555) 987-6543',
        patterns: ['phones']
      });

      expect(result.extracted.phones.length).toBe(2);
    });

    test('should extract all patterns', async () => {
      const result = await dataTool.execute({
        action: 'extract_data',
        text: 'Visit https://example.com, email test@example.com, or call 555-1234',
        patterns: 'all'
      });

      expect(result.extracted.urls).toBeDefined();
      expect(result.extracted.emails).toBeDefined();
      expect(result.extracted.phones).toBeDefined();
    });

    test('should redact sensitive data', async () => {
      const result = await dataTool.execute({
        action: 'extract_data',
        text: 'Card: 1234-5678-9012-3456, SSN: 123-45-6789',
        patterns: 'all'
      });

      // Check that credit cards and SSNs are redacted
      if (result.extracted.creditCards && result.extracted.creditCards.length > 0) {
        expect(result.extracted.creditCards[0]).toContain('*');
      }
      if (result.extracted.ssn && result.extracted.ssn.length > 0) {
        expect(result.extracted.ssn[0]).toContain('***-**');
      }
    });
  });

  describe('Data Formatting', () => {
    test('should format data as JSON', async () => {
      const result = await dataTool.execute({
        action: 'format_data',
        data: { key: 'value' },
        format: 'json'
      });

      expect(result.format).toBe('json');
      expect(result.formatted).toContain('"key"');
      expect(result.formatted).toContain('"value"');
    });

    test('should format data as CSV', async () => {
      const result = await dataTool.execute({
        action: 'format_data',
        data: [
          { name: 'John', age: 30 },
          { name: 'Jane', age: 25 }
        ],
        format: 'csv'
      });

      expect(result.format).toBe('csv');
      expect(result.formatted).toContain('name,age');
      expect(result.formatted).toContain('John,30');
    });

    test('should format data as markdown table', async () => {
      const result = await dataTool.execute({
        action: 'format_data',
        data: [{ col1: 'val1', col2: 'val2' }],
        format: 'markdown'
      });

      expect(result.format).toBe('markdown');
      expect(result.formatted).toContain('|');
      expect(result.formatted).toContain('---');
    });
  });

  describe('Calculations', () => {
    test('should perform basic calculations', async () => {
      const result = await dataTool.execute({
        action: 'calculate',
        expression: '2 + 3 * 4'
      });

      expect(result.result).toBe(14); // 2 + 12
      expect(result.summary).toContain('= 14');
    });

    test('should perform calculations with variables', async () => {
      const result = await dataTool.execute({
        action: 'calculate',
        expression: 'x + y * z',
        values: { x: 2, y: 3, z: 4 }
      });

      expect(result.result).toBe(14);
    });

    test('should reject invalid expressions', async () => {
      await expect(dataTool.execute({
        action: 'calculate',
        expression: 'alert("hack")'
      })).rejects.toThrow('Invalid expression');
    });
  });

  describe('Data Transformation', () => {
    test('should filter data', async () => {
      const result = await dataTool.execute({
        action: 'filter',
        data: [
          { name: 'John', age: 30 },
          { name: 'Jane', age: 25 },
          { name: 'Bob', age: 30 }
        ],
        conditions: [
          { field: 'age', operator: '=', value: 30 }
        ]
      });

      expect(result.filteredCount).toBe(2);
      expect(result.filtered.length).toBe(2);
    });

    test('should sort data', async () => {
      const result = await dataTool.execute({
        action: 'sort',
        data: [
          { name: 'Charlie', age: 35 },
          { name: 'Alice', age: 25 },
          { name: 'Bob', age: 30 }
        ],
        field: 'name',
        order: 'asc'
      });

      expect(result.sorted[0].name).toBe('Alice');
      expect(result.sorted[2].name).toBe('Charlie');
    });

    test('should aggregate data', async () => {
      const result = await dataTool.execute({
        action: 'aggregate',
        data: [10, 20, 30, 40, 50],
        metrics: ['count', 'sum', 'mean', 'min', 'max']
      });

      expect(result.aggregated.total.count).toBe(5);
      expect(result.aggregated.total.sum).toBe(150);
      expect(result.aggregated.total.mean).toBe(30);
      expect(result.aggregated.total.min).toBe(10);
      expect(result.aggregated.total.max).toBe(50);
    });
  });

  describe('Encoding and Hashing', () => {
    test('should encode data as base64', async () => {
      const result = await dataTool.execute({
        action: 'encode',
        text: 'Hello World',
        encoding: 'base64'
      });

      expect(result.encoding).toBe('base64');
      expect(result.encoded).toBe('SGVsbG8gV29ybGQ=');
    });

    test('should decode base64 data', async () => {
      const result = await dataTool.execute({
        action: 'decode',
        text: 'SGVsbG8gV29ybGQ=',
        encoding: 'base64'
      });

      expect(result.decoded).toBe('Hello World');
    });

    test('should generate hash', async () => {
      const result = await dataTool.execute({
        action: 'hash',
        text: 'test data',
        algorithm: 'sha256'
      });

      expect(result.algorithm).toBe('sha256');
      expect(result.hash).toBeDefined();
      expect(result.hash.length).toBe(64); // SHA256 produces 64 hex characters
    });
  });

  describe('Data Validation', () => {
    test('should validate data against rules', async () => {
      const result = await dataTool.execute({
        action: 'validate',
        data: {
          email: 'test@example.com',
          age: 25
        },
        rules: [
          { field: 'email', required: true, pattern: '^[\\w.-]+@[\\w.-]+\\.\\w+$' },
          { field: 'age', required: true, type: 'number', min: 18, max: 100 }
        ]
      });

      expect(result.valid).toBe(true);
      expect(result.errors.length).toBe(0);
    });

    test('should report validation errors', async () => {
      const result = await dataTool.execute({
        action: 'validate',
        data: {
          email: 'invalid-email',
          age: 150
        },
        rules: [
          { field: 'email', pattern: '^[\\w.-]+@[\\w.-]+\\.\\w+$' },
          { field: 'age', max: 100 }
        ]
      });

      expect(result.valid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });

  describe('CSV Parsing', () => {
    test('should parse CSV with headers', async () => {
      const result = await dataTool.execute({
        action: 'parse_csv',
        text: 'name,age\nJohn,30\nJane,25',
        hasHeaders: true
      });

      expect(result.data.length).toBe(2);
      expect(result.data[0].name).toBe('John');
      expect(result.data[0].age).toBe('30');
      expect(result.headers).toEqual(['name', 'age']);
    });

    test('should parse CSV without headers', async () => {
      const result = await dataTool.execute({
        action: 'parse_csv',
        text: 'John,30\nJane,25',
        hasHeaders: false
      });

      expect(result.data.length).toBe(2);
      expect(result.data[0]).toEqual(['John', '30']);
    });
  });

  describe('JSON Parsing', () => {
    test('should parse valid JSON', async () => {
      const result = await dataTool.execute({
        action: 'parse_json',
        text: '{"name": "John", "age": 30}'
      });

      expect(result.parsed.name).toBe('John');
      expect(result.parsed.age).toBe(30);
      expect(result.type).toBe('object');
    });

    test('should fix common JSON issues in non-strict mode', async () => {
      const result = await dataTool.execute({
        action: 'parse_json',
        text: "{name: 'John', age: 30,}",
        strict: false
      });

      expect(result.parsed.name).toBe('John');
      expect(result.parsed.age).toBe(30);
    });
  });
});

describe('Tool Integration', () => {
  test('tools should register with email agent', () => {
    const mockAgent = {
      registerTool: jest.fn()
    };

    playwrightTool.register(mockAgent);
    calendarTool.register(mockAgent);
    dataTool.register(mockAgent);

    expect(mockAgent.registerTool).toHaveBeenCalledTimes(3);
    expect(mockAgent.registerTool).toHaveBeenCalledWith('playwright', playwrightTool);
    expect(mockAgent.registerTool).toHaveBeenCalledWith('calendar', calendarTool);
    expect(mockAgent.registerTool).toHaveBeenCalledWith('data', dataTool);
  });

  test('tools should handle concurrent execution', async () => {
    const promises = [
      dataTool.execute({ action: 'analyze_text', text: 'test' }),
      dataTool.execute({ action: 'calculate', expression: '1+1' }),
      dataTool.execute({ action: 'encode', text: 'test', encoding: 'base64' })
    ];

    const results = await Promise.all(promises);

    expect(results).toHaveLength(3);
    expect(results[0].wordCount).toBe(1);
    expect(results[1].result).toBe(2);
    expect(results[2].encoded).toBe('dGVzdA==');
  });
});