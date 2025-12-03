/**
 * Data Processing Tool
 * Analyze and process data for email agent
 */

const logger = require('../logger');
const crypto = require('crypto');

class DataTool {
  constructor() {
    this.name = 'data';
    this.description = 'Data analysis and processing';
  }

  /**
   * Execute data action
   */
  async execute(parameters) {
    const { action, ...params } = parameters;

    logger.info('Executing data action', { action, params });

    switch (action) {
      case 'analyze_text':
        return await this.analyzeText(params);
      case 'extract_data':
        return await this.extractData(params);
      case 'format_data':
        return await this.formatData(params);
      case 'calculate':
        return await this.calculate(params);
      case 'parse_json':
        return await this.parseJSON(params);
      case 'parse_csv':
        return await this.parseCSV(params);
      case 'transform_data':
        return await this.transformData(params);
      case 'aggregate':
        return await this.aggregateData(params);
      case 'filter':
        return await this.filterData(params);
      case 'sort':
        return await this.sortData(params);
      case 'encode':
        return await this.encodeData(params);
      case 'decode':
        return await this.decodeData(params);
      case 'hash':
        return await this.hashData(params);
      case 'validate':
        return await this.validateData(params);
      case 'summarize':
        return await this.summarizeData(params);
      default:
        throw new Error(`Unknown data action: ${action}`);
    }
  }

  /**
   * Analyze text
   */
  async analyzeText(params) {
    const { text, detailed = false } = params;

    logger.info('Analyzing text', { length: text.length });

    const words = text.split(/\s+/).filter(w => w.length > 0);
    const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
    const paragraphs = text.split(/\n\n+/).filter(p => p.trim().length > 0);

    const analysis = {
      wordCount: words.length,
      charCount: text.length,
      charCountNoSpaces: text.replace(/\s/g, '').length,
      sentences: sentences.length,
      paragraphs: paragraphs.length,
      avgWordLength: words.length > 0 ? (words.reduce((sum, w) => sum + w.length, 0) / words.length).toFixed(1) : 0,
      avgSentenceLength: sentences.length > 0 ? (words.length / sentences.length).toFixed(1) : 0
    };

    if (detailed) {
      // Add detailed analysis
      const wordFrequency = {};
      words.forEach(word => {
        const lower = word.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (lower) {
          wordFrequency[lower] = (wordFrequency[lower] || 0) + 1;
        }
      });

      // Sort by frequency
      const topWords = Object.entries(wordFrequency)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([word, count]) => ({ word, count }));

      analysis.topWords = topWords;
      analysis.uniqueWords = Object.keys(wordFrequency).length;

      // Detect language patterns
      analysis.hasQuestions = /\?/.test(text);
      analysis.hasExclamations = /!/.test(text);
      analysis.hasNumbers = /\d/.test(text);
      analysis.hasUrls = /https?:\/\/[^\s]+/.test(text);
      analysis.hasEmails = /[\w.-]+@[\w.-]+\.\w+/.test(text);
    }

    return {
      ...analysis,
      summary: `Text contains ${analysis.wordCount} words, ${analysis.sentences} sentences, ${analysis.paragraphs} paragraphs`
    };
  }

  /**
   * Extract structured data
   */
  async extractData(params) {
    const { text, patterns = 'all', customPattern = null } = params;

    logger.info('Extracting data', { patterns });

    const extracted = {};

    // Standard patterns
    const standardPatterns = {
      emails: /[\w.-]+@[\w.-]+\.\w+/g,
      phones: /(?:\+?1[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}/g,
      urls: /https?:\/\/[^\s<>"{}|\\^`\[\]]+/g,
      dates: /(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})|(\d{4}[-/]\d{1,2}[-/]\d{1,2})|([A-Z][a-z]+ \d{1,2},? \d{4})/g,
      times: /\b([01]?[0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?(?:\s?[AP]M)?\b/gi,
      ips: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,
      hashtags: /#\w+/g,
      mentions: /@\w+/g,
      money: /\$[\d,]+(?:\.\d{2})?|\b\d+(?:\.\d{2})?\s?(?:USD|EUR|GBP)/g,
      percents: /\d+(?:\.\d+)?%/g,
      creditCards: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g, // Basic pattern, redact in production
      ssn: /\b\d{3}-\d{2}-\d{4}\b/g, // Basic pattern, redact in production
      zip: /\b\d{5}(?:-\d{4})?\b/g
    };

    if (patterns === 'all' || Array.isArray(patterns)) {
      const patternsToUse = patterns === 'all' ? Object.keys(standardPatterns) : patterns;

      for (const patternName of patternsToUse) {
        if (standardPatterns[patternName]) {
          const matches = text.match(standardPatterns[patternName]) || [];
          extracted[patternName] = [...new Set(matches)]; // Remove duplicates
        }
      }
    }

    // Custom pattern
    if (customPattern) {
      try {
        const regex = new RegExp(customPattern, 'g');
        extracted.custom = text.match(regex) || [];
      } catch (error) {
        logger.error('Invalid custom pattern', { customPattern, error: error.message });
      }
    }

    // Redact sensitive data
    if (extracted.creditCards) {
      extracted.creditCards = extracted.creditCards.map(cc =>
        cc.replace(/\d(?=\d{4})/g, '*')
      );
    }
    if (extracted.ssn) {
      extracted.ssn = extracted.ssn.map(ssn =>
        ssn.replace(/\d{3}-\d{2}/, '***-**')
      );
    }

    const totalExtracted = Object.values(extracted).reduce((sum, arr) => sum + arr.length, 0);

    return {
      extracted,
      counts: Object.fromEntries(
        Object.entries(extracted).map(([key, values]) => [key, values.length])
      ),
      total: totalExtracted,
      summary: `Extracted ${totalExtracted} data points across ${Object.keys(extracted).length} categories`
    };
  }

  /**
   * Format data
   */
  async formatData(params) {
    const { data, format, options = {} } = params;

    logger.info('Formatting data', { format });

    let formatted;

    switch (format.toLowerCase()) {
      case 'json':
        formatted = JSON.stringify(data, null, options.indent || 2);
        break;

      case 'csv':
        formatted = this.toCSV(data, options);
        break;

      case 'tsv':
        formatted = this.toCSV(data, { ...options, delimiter: '\t' });
        break;

      case 'markdown':
        formatted = this.toMarkdown(data, options);
        break;

      case 'html':
        formatted = this.toHTML(data, options);
        break;

      case 'xml':
        formatted = this.toXML(data, options);
        break;

      case 'yaml':
        formatted = this.toYAML(data, options);
        break;

      default:
        formatted = String(data);
    }

    return {
      formatted,
      format: format.toLowerCase(),
      size: formatted.length,
      summary: `Data formatted as ${format}`
    };
  }

  /**
   * Perform calculations
   */
  async calculate(params) {
    const { expression, values = {} } = params;

    logger.info('Calculating expression', { expression });

    try {
      // Safe math evaluation
      let safeExpression = expression;

      // Replace variables with values
      Object.entries(values).forEach(([key, value]) => {
        const regex = new RegExp(`\\b${key}\\b`, 'g');
        safeExpression = safeExpression.replace(regex, value);
      });

      // Allow only safe math operations
      if (!/^[\d\s+\-*/().,]+$/.test(safeExpression)) {
        throw new Error('Expression contains invalid characters');
      }

      // Use Function constructor for safer evaluation than eval
      const result = new Function('return ' + safeExpression)();

      return {
        expression,
        evaluatedExpression: safeExpression,
        result,
        type: typeof result,
        summary: `${expression} = ${result}`
      };
    } catch (error) {
      throw new Error(`Invalid expression: ${error.message}`);
    }
  }

  /**
   * Parse JSON data
   */
  async parseJSON(params) {
    const { text, strict = true } = params;

    logger.info('Parsing JSON', { strict });

    try {
      let parsed;

      if (strict) {
        parsed = JSON.parse(text);
      } else {
        // Try to fix common JSON issues
        let fixed = text
          .replace(/'/g, '"') // Single to double quotes
          .replace(/(\w+):/g, '"$1":') // Unquoted keys
          .replace(/,\s*}/g, '}') // Trailing commas
          .replace(/,\s*]/g, ']');

        parsed = JSON.parse(fixed);
      }

      return {
        parsed,
        type: Array.isArray(parsed) ? 'array' : typeof parsed,
        keys: typeof parsed === 'object' && !Array.isArray(parsed) ? Object.keys(parsed) : null,
        length: Array.isArray(parsed) ? parsed.length : null,
        summary: `Successfully parsed JSON ${Array.isArray(parsed) ? `array with ${parsed.length} items` : 'object'}`
      };
    } catch (error) {
      throw new Error(`Failed to parse JSON: ${error.message}`);
    }
  }

  /**
   * Parse CSV data
   */
  async parseCSV(params) {
    const { text, hasHeaders = true, delimiter = ',', quote = '"' } = params;

    logger.info('Parsing CSV');

    try {
      const lines = text.trim().split(/\r?\n/);
      const headers = hasHeaders ? lines[0].split(delimiter).map(h => h.trim().replace(/^"|"$/g, '')) : null;
      const dataLines = hasHeaders ? lines.slice(1) : lines;

      const data = dataLines.map(line => {
        const values = this.parseCSVLine(line, delimiter, quote);

        if (hasHeaders) {
          const row = {};
          headers.forEach((header, index) => {
            row[header] = values[index] || null;
          });
          return row;
        }

        return values;
      });

      return {
        data,
        headers,
        rows: data.length,
        columns: headers ? headers.length : (data[0] ? data[0].length : 0),
        summary: `Parsed CSV with ${data.length} rows and ${headers ? headers.length : 'unknown'} columns`
      };
    } catch (error) {
      throw new Error(`Failed to parse CSV: ${error.message}`);
    }
  }

  /**
   * Parse a CSV line handling quotes
   */
  parseCSVLine(line, delimiter, quote) {
    const values = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const nextChar = line[i + 1];

      if (char === quote) {
        if (inQuotes && nextChar === quote) {
          current += quote;
          i++; // Skip next quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === delimiter && !inQuotes) {
        values.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }

    values.push(current.trim());
    return values;
  }

  /**
   * Transform data
   */
  async transformData(params) {
    const { data, operation, field = null, newField = null, value = null } = params;

    logger.info('Transforming data', { operation });

    let transformed;

    switch (operation) {
      case 'map':
        if (!Array.isArray(data)) throw new Error('Data must be an array for map operation');
        transformed = data.map(item => {
          if (field && newField) {
            return { ...item, [newField]: item[field] };
          }
          return item;
        });
        break;

      case 'filter':
        if (!Array.isArray(data)) throw new Error('Data must be an array for filter operation');
        transformed = data.filter(item => {
          if (field && value !== null) {
            return item[field] === value;
          }
          return true;
        });
        break;

      case 'reduce':
        if (!Array.isArray(data)) throw new Error('Data must be an array for reduce operation');
        transformed = data.reduce((acc, item) => {
          if (field && item[field] !== undefined) {
            return acc + (typeof item[field] === 'number' ? item[field] : 0);
          }
          return acc;
        }, 0);
        break;

      case 'flatten':
        transformed = this.flatten(data);
        break;

      case 'group':
        if (!Array.isArray(data) || !field) throw new Error('Data must be an array with field for group operation');
        transformed = this.groupBy(data, field);
        break;

      case 'pivot':
        if (!Array.isArray(data)) throw new Error('Data must be an array for pivot operation');
        transformed = this.pivot(data, field, newField, value);
        break;

      default:
        transformed = data;
    }

    return {
      transformed,
      operation,
      originalCount: Array.isArray(data) ? data.length : null,
      transformedCount: Array.isArray(transformed) ? transformed.length : null,
      summary: `Data transformed using ${operation} operation`
    };
  }

  /**
   * Aggregate data
   */
  async aggregateData(params) {
    const { data, groupBy = null, metrics = ['count'] } = params;

    logger.info('Aggregating data', { groupBy, metrics });

    if (!Array.isArray(data)) {
      throw new Error('Data must be an array for aggregation');
    }

    const aggregated = {};

    if (groupBy) {
      // Group and aggregate
      const groups = this.groupBy(data, groupBy);

      Object.entries(groups).forEach(([key, items]) => {
        aggregated[key] = this.calculateMetrics(items, metrics);
      });
    } else {
      // Aggregate all data
      aggregated.total = this.calculateMetrics(data, metrics);
    }

    return {
      aggregated,
      groups: Object.keys(aggregated).length,
      metrics,
      summary: `Aggregated data into ${Object.keys(aggregated).length} groups`
    };
  }

  /**
   * Calculate metrics for a dataset
   */
  calculateMetrics(data, metrics) {
    const results = {};

    metrics.forEach(metric => {
      switch (metric) {
        case 'count':
          results.count = data.length;
          break;

        case 'sum':
          results.sum = data.reduce((acc, item) => {
            const val = typeof item === 'number' ? item : (item.value || 0);
            return acc + val;
          }, 0);
          break;

        case 'avg':
        case 'mean':
          const sum = data.reduce((acc, item) => {
            const val = typeof item === 'number' ? item : (item.value || 0);
            return acc + val;
          }, 0);
          results[metric] = data.length > 0 ? sum / data.length : 0;
          break;

        case 'min':
          results.min = Math.min(...data.map(item =>
            typeof item === 'number' ? item : (item.value || 0)
          ));
          break;

        case 'max':
          results.max = Math.max(...data.map(item =>
            typeof item === 'number' ? item : (item.value || 0)
          ));
          break;

        case 'median':
          const values = data.map(item =>
            typeof item === 'number' ? item : (item.value || 0)
          ).sort((a, b) => a - b);
          const mid = Math.floor(values.length / 2);
          results.median = values.length % 2
            ? values[mid]
            : (values[mid - 1] + values[mid]) / 2;
          break;
      }
    });

    return results;
  }

  /**
   * Filter data
   */
  async filterData(params) {
    const { data, conditions, logic = 'AND' } = params;

    logger.info('Filtering data', { conditions, logic });

    if (!Array.isArray(data)) {
      throw new Error('Data must be an array for filtering');
    }

    const filtered = data.filter(item => {
      const results = conditions.map(condition => {
        const { field, operator, value } = condition;
        const itemValue = item[field];

        switch (operator) {
          case '=':
          case '==':
            return itemValue == value;
          case '===':
            return itemValue === value;
          case '!=':
          case '!==':
            return itemValue != value;
          case '>':
            return itemValue > value;
          case '>=':
            return itemValue >= value;
          case '<':
            return itemValue < value;
          case '<=':
            return itemValue <= value;
          case 'contains':
            return String(itemValue).includes(String(value));
          case 'startsWith':
            return String(itemValue).startsWith(String(value));
          case 'endsWith':
            return String(itemValue).endsWith(String(value));
          case 'in':
            return Array.isArray(value) ? value.includes(itemValue) : false;
          case 'notIn':
            return Array.isArray(value) ? !value.includes(itemValue) : true;
          case 'regex':
            return new RegExp(value).test(String(itemValue));
          default:
            return false;
        }
      });

      return logic === 'AND'
        ? results.every(r => r)
        : results.some(r => r);
    });

    return {
      filtered,
      originalCount: data.length,
      filteredCount: filtered.length,
      removed: data.length - filtered.length,
      summary: `Filtered ${data.length} items to ${filtered.length} items`
    };
  }

  /**
   * Sort data
   */
  async sortData(params) {
    const { data, field, order = 'asc', fields = null } = params;

    logger.info('Sorting data', { field, order, fields });

    if (!Array.isArray(data)) {
      throw new Error('Data must be an array for sorting');
    }

    const sorted = [...data]; // Create copy

    if (fields && Array.isArray(fields)) {
      // Multi-field sorting
      sorted.sort((a, b) => {
        for (const sortField of fields) {
          const { field: f, order: o = 'asc' } = sortField;
          const comparison = this.compareValues(a[f], b[f]);

          if (comparison !== 0) {
            return o === 'asc' ? comparison : -comparison;
          }
        }
        return 0;
      });
    } else if (field) {
      // Single field sorting
      sorted.sort((a, b) => {
        const comparison = this.compareValues(a[field], b[field]);
        return order === 'asc' ? comparison : -comparison;
      });
    }

    return {
      sorted,
      count: sorted.length,
      field,
      order,
      summary: `Sorted ${sorted.length} items by ${field || 'multiple fields'} in ${order} order`
    };
  }

  /**
   * Compare values for sorting
   */
  compareValues(a, b) {
    if (a === b) return 0;
    if (a === null || a === undefined) return 1;
    if (b === null || b === undefined) return -1;

    if (typeof a === 'number' && typeof b === 'number') {
      return a - b;
    }

    return String(a).localeCompare(String(b));
  }

  /**
   * Encode data
   */
  async encodeData(params) {
    const { text, encoding = 'base64' } = params;

    logger.info('Encoding data', { encoding });

    let encoded;

    switch (encoding.toLowerCase()) {
      case 'base64':
        encoded = Buffer.from(text).toString('base64');
        break;

      case 'hex':
        encoded = Buffer.from(text).toString('hex');
        break;

      case 'url':
        encoded = encodeURIComponent(text);
        break;

      case 'html':
        encoded = text
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#39;');
        break;

      default:
        throw new Error(`Unsupported encoding: ${encoding}`);
    }

    return {
      encoded,
      encoding,
      originalLength: text.length,
      encodedLength: encoded.length,
      summary: `Encoded ${text.length} characters as ${encoding}`
    };
  }

  /**
   * Decode data
   */
  async decodeData(params) {
    const { text, encoding = 'base64' } = params;

    logger.info('Decoding data', { encoding });

    let decoded;

    try {
      switch (encoding.toLowerCase()) {
        case 'base64':
          decoded = Buffer.from(text, 'base64').toString('utf-8');
          break;

        case 'hex':
          decoded = Buffer.from(text, 'hex').toString('utf-8');
          break;

        case 'url':
          decoded = decodeURIComponent(text);
          break;

        case 'html':
          decoded = text
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>')
            .replace(/&quot;/g, '"')
            .replace(/&#39;/g, "'")
            .replace(/&amp;/g, '&');
          break;

        default:
          throw new Error(`Unsupported encoding: ${encoding}`);
      }
    } catch (error) {
      throw new Error(`Failed to decode: ${error.message}`);
    }

    return {
      decoded,
      encoding,
      originalLength: text.length,
      decodedLength: decoded.length,
      summary: `Decoded ${text.length} characters from ${encoding}`
    };
  }

  /**
   * Hash data
   */
  async hashData(params) {
    const { text, algorithm = 'sha256', encoding = 'hex' } = params;

    logger.info('Hashing data', { algorithm });

    const hash = crypto
      .createHash(algorithm)
      .update(text)
      .digest(encoding);

    return {
      hash,
      algorithm,
      encoding,
      length: hash.length,
      summary: `Generated ${algorithm} hash: ${hash.substring(0, 16)}...`
    };
  }

  /**
   * Validate data
   */
  async validateData(params) {
    const { data, schema, rules = [] } = params;

    logger.info('Validating data');

    const errors = [];
    const warnings = [];

    // Apply validation rules
    rules.forEach(rule => {
      const { field, type, required, min, max, pattern, custom } = rule;

      if (field) {
        const value = data[field];

        // Required check
        if (required && (value === undefined || value === null || value === '')) {
          errors.push(`Field '${field}' is required`);
          return;
        }

        if (value === undefined || value === null) {
          return; // Skip other checks if not required and not present
        }

        // Type check
        if (type && typeof value !== type) {
          errors.push(`Field '${field}' must be of type ${type}`);
        }

        // Length/value checks
        if (typeof value === 'string') {
          if (min && value.length < min) {
            errors.push(`Field '${field}' must be at least ${min} characters`);
          }
          if (max && value.length > max) {
            errors.push(`Field '${field}' must be at most ${max} characters`);
          }
        } else if (typeof value === 'number') {
          if (min !== undefined && value < min) {
            errors.push(`Field '${field}' must be at least ${min}`);
          }
          if (max !== undefined && value > max) {
            errors.push(`Field '${field}' must be at most ${max}`);
          }
        }

        // Pattern check
        if (pattern && !new RegExp(pattern).test(String(value))) {
          errors.push(`Field '${field}' does not match required pattern`);
        }

        // Custom validation
        if (custom && typeof custom === 'function') {
          const result = custom(value, data);
          if (result !== true) {
            errors.push(result || `Field '${field}' failed custom validation`);
          }
        }
      }
    });

    const isValid = errors.length === 0;

    return {
      valid: isValid,
      errors,
      warnings,
      summary: isValid ? 'Data is valid' : `Validation failed with ${errors.length} errors`
    };
  }

  /**
   * Summarize data
   */
  async summarizeData(params) {
    const { data, maxLength = 500 } = params;

    logger.info('Summarizing data');

    let summary = {};

    if (Array.isArray(data)) {
      summary = {
        type: 'array',
        length: data.length,
        sample: data.slice(0, 3),
        dataTypes: [...new Set(data.map(item => typeof item))],
      };

      if (data.length > 0 && typeof data[0] === 'object') {
        summary.fields = Object.keys(data[0]);
        summary.fieldCount = summary.fields.length;
      }
    } else if (typeof data === 'object' && data !== null) {
      summary = {
        type: 'object',
        fields: Object.keys(data),
        fieldCount: Object.keys(data).length,
        sample: {}
      };

      // Sample first few fields
      Object.keys(data).slice(0, 5).forEach(key => {
        summary.sample[key] = data[key];
      });
    } else {
      summary = {
        type: typeof data,
        value: String(data).substring(0, maxLength),
        length: String(data).length
      };
    }

    return {
      summary,
      description: this.generateDescription(summary),
      summary: `Generated summary of ${summary.type} data`
    };
  }

  /**
   * Generate human-readable description
   */
  generateDescription(summary) {
    if (summary.type === 'array') {
      return `Array with ${summary.length} items${summary.fields ? `, each containing ${summary.fieldCount} fields: ${summary.fields.slice(0, 3).join(', ')}${summary.fields.length > 3 ? '...' : ''}` : ''}`;
    } else if (summary.type === 'object') {
      return `Object with ${summary.fieldCount} fields: ${summary.fields.slice(0, 5).join(', ')}${summary.fields.length > 5 ? '...' : ''}`;
    } else {
      return `${summary.type} value${summary.length ? ` of length ${summary.length}` : ''}`;
    }
  }

  /**
   * Helper: Convert to CSV
   */
  toCSV(data, options = {}) {
    const { delimiter = ',', includeHeaders = true, quote = '"' } = options;

    if (!Array.isArray(data) || data.length === 0) return '';

    const headers = Object.keys(data[0] || {});
    const rows = data.map(row =>
      headers.map(h => {
        const value = row[h] || '';
        const strValue = String(value);

        // Quote if contains delimiter, quote, or newline
        if (strValue.includes(delimiter) || strValue.includes(quote) || strValue.includes('\n')) {
          return `${quote}${strValue.replace(new RegExp(quote, 'g'), quote + quote)}${quote}`;
        }

        return strValue;
      }).join(delimiter)
    );

    return includeHeaders
      ? [headers.join(delimiter), ...rows].join('\n')
      : rows.join('\n');
  }

  /**
   * Helper: Convert to Markdown table
   */
  toMarkdown(data, options = {}) {
    if (!Array.isArray(data) || data.length === 0) return '';

    const headers = Object.keys(data[0] || {});
    const headerRow = `| ${headers.join(' | ')} |`;
    const separatorRow = `| ${headers.map(() => '---').join(' | ')} |`;

    const rows = data.map(row =>
      `| ${headers.map(h => String(row[h] || '')).join(' | ')} |`
    );

    return [headerRow, separatorRow, ...rows].join('\n');
  }

  /**
   * Helper: Convert to HTML table
   */
  toHTML(data, options = {}) {
    const { tableClass = '', includeStyles = false } = options;

    if (!Array.isArray(data) || data.length === 0) return '<table></table>';

    const headers = Object.keys(data[0] || {});

    let html = `<table${tableClass ? ` class="${tableClass}"` : ''}>`;

    if (includeStyles) {
      html = `<style>
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
      </style>` + html;
    }

    html += '<thead><tr>';
    headers.forEach(h => {
      html += `<th>${this.escapeHTML(h)}</th>`;
    });
    html += '</tr></thead><tbody>';

    data.forEach(row => {
      html += '<tr>';
      headers.forEach(h => {
        html += `<td>${this.escapeHTML(String(row[h] || ''))}</td>`;
      });
      html += '</tr>';
    });

    html += '</tbody></table>';
    return html;
  }

  /**
   * Helper: Convert to XML
   */
  toXML(data, options = {}) {
    const { rootName = 'data', itemName = 'item' } = options;

    const toXMLValue = (value, key) => {
      if (value === null || value === undefined) return `<${key}/>`;

      if (typeof value === 'object') {
        if (Array.isArray(value)) {
          return value.map(v => `<${key}>${this.escapeXML(String(v))}</${key}>`).join('');
        }

        let xml = `<${key}>`;
        Object.entries(value).forEach(([k, v]) => {
          xml += toXMLValue(v, k);
        });
        xml += `</${key}>`;
        return xml;
      }

      return `<${key}>${this.escapeXML(String(value))}</${key}>`;
    };

    let xml = `<?xml version="1.0" encoding="UTF-8"?><${rootName}>`;

    if (Array.isArray(data)) {
      data.forEach(item => {
        xml += `<${itemName}>`;
        if (typeof item === 'object' && item !== null) {
          Object.entries(item).forEach(([key, value]) => {
            xml += toXMLValue(value, key);
          });
        } else {
          xml += this.escapeXML(String(item));
        }
        xml += `</${itemName}>`;
      });
    } else if (typeof data === 'object' && data !== null) {
      Object.entries(data).forEach(([key, value]) => {
        xml += toXMLValue(value, key);
      });
    } else {
      xml += this.escapeXML(String(data));
    }

    xml += `</${rootName}>`;
    return xml;
  }

  /**
   * Helper: Convert to YAML
   */
  toYAML(data, options = {}) {
    const { indent = 2 } = options;

    const toYAMLValue = (value, depth = 0) => {
      const spacing = ' '.repeat(depth * indent);

      if (value === null || value === undefined) return 'null';
      if (typeof value === 'boolean') return value.toString();
      if (typeof value === 'number') return value.toString();
      if (typeof value === 'string') {
        // Quote if contains special characters
        if (/[:\{\}\[\],&*#?|<>=!%@\\]/.test(value) || value.includes('\n')) {
          return `"${value.replace(/"/g, '\\"')}"`;
        }
        return value;
      }

      if (Array.isArray(value)) {
        if (value.length === 0) return '[]';
        return '\n' + value.map(item =>
          `${spacing}- ${typeof item === 'object' ? toYAMLValue(item, depth + 1).trim() : toYAMLValue(item)}`
        ).join('\n');
      }

      if (typeof value === 'object') {
        const entries = Object.entries(value);
        if (entries.length === 0) return '{}';
        return '\n' + entries.map(([k, v]) =>
          `${spacing}${k}: ${toYAMLValue(v, depth + 1)}`
        ).join('\n');
      }

      return String(value);
    };

    return toYAMLValue(data).trim();
  }

  /**
   * Helper: Escape HTML
   */
  escapeHTML(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Helper: Escape XML
   */
  escapeXML(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  /**
   * Helper: Flatten nested data
   */
  flatten(obj, prefix = '') {
    const flattened = {};

    Object.entries(obj).forEach(([key, value]) => {
      const newKey = prefix ? `${prefix}.${key}` : key;

      if (value === null || value === undefined) {
        flattened[newKey] = value;
      } else if (typeof value === 'object' && !Array.isArray(value)) {
        Object.assign(flattened, this.flatten(value, newKey));
      } else {
        flattened[newKey] = value;
      }
    });

    return flattened;
  }

  /**
   * Helper: Group by field
   */
  groupBy(data, field) {
    return data.reduce((groups, item) => {
      const key = item[field];
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
      return groups;
    }, {});
  }

  /**
   * Helper: Pivot data
   */
  pivot(data, rowField, colField, valueField) {
    const pivoted = {};

    data.forEach(item => {
      const row = item[rowField];
      const col = item[colField];
      const val = item[valueField];

      if (!pivoted[row]) pivoted[row] = {};
      pivoted[row][col] = val;
    });

    return pivoted;
  }

  /**
   * Register with email agent
   */
  register(emailAgent) {
    emailAgent.registerTool(this.name, this);
    logger.info('Data tool registered with email agent');
  }
}

module.exports = new DataTool();
module.exports.DataTool = DataTool;
