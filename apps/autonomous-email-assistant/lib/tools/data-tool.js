/**
 * Data Processing Tool
 * Analyze and process data for email agent
 */

const logger = require('../logger');

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
      default:
        throw new Error(`Unknown data action: ${action}`);
    }
  }

  /**
   * Analyze text
   */
  async analyzeText(params) {
    const { text } = params;

    logger.info('Analyzing text', { length: text.length });

    const wordCount = text.split(/\s+/).length;
    const charCount = text.length;
    const sentences = text.split(/[.!?]+/).length;

    return {
      wordCount,
      charCount,
      sentences,
      avgWordLength: (charCount / wordCount).toFixed(1),
      summary: `Text contains ${wordCount} words, ${sentences} sentences`
    };
  }

  /**
   * Extract structured data
   */
  async extractData(params) {
    const { text, pattern } = params;

    logger.info('Extracting data');

    // Extract emails
    const emails = text.match(/[\w.-]+@[\w.-]+\.\w+/g) || [];

    // Extract phone numbers
    const phones = text.match(/\d{3}[-.]?\d{3}[-.]?\d{4}/g) || [];

    // Extract URLs
    const urls = text.match(/https?:\/\/[^\s]+/g) || [];

    // Extract dates
    const dates = text.match(/\d{1,2}\/\d{1,2}\/\d{2,4}/g) || [];

    return {
      emails,
      phones,
      urls,
      dates,
      summary: `Extracted ${emails.length} emails, ${phones.length} phones, ${urls.length} URLs`
    };
  }

  /**
   * Format data
   */
  async formatData(params) {
    const { data, format } = params;

    logger.info('Formatting data', { format });

    if (format === 'json') {
      return {
        formatted: JSON.stringify(data, null, 2),
        format: 'json'
      };
    }

    if (format === 'csv') {
      // Convert to CSV
      return {
        formatted: this.toCSV(data),
        format: 'csv'
      };
    }

    return {
      formatted: data,
      format: 'raw'
    };
  }

  /**
   * Perform calculations
   */
  async calculate(params) {
    const { expression } = params;

    logger.info('Calculating expression', { expression });

    try {
      // Safe evaluation - in production use a proper math parser
      const result = eval(expression);

      return {
        expression,
        result,
        summary: `${expression} = ${result}`
      };
    } catch (error) {
      throw new Error(`Invalid expression: ${error.message}`);
    }
  }

  /**
   * Convert to CSV
   */
  toCSV(data) {
    if (!Array.isArray(data)) return '';

    const headers = Object.keys(data[0] || {});
    const rows = data.map(row =>
      headers.map(h => row[h] || '').join(',')
    );

    return [headers.join(','), ...rows].join('\n');
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
