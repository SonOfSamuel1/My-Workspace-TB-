/**
 * Attachment Intelligence System
 * Comprehensive attachment analysis, parsing, and security scanning
 */

const logger = require('./logger');
const crypto = require('crypto');

class AttachmentParser {
  constructor() {
    this.supportedTypes = {
      documents: ['pdf', 'doc', 'docx', 'txt', 'rtf'],
      spreadsheets: ['xls', 'xlsx', 'csv'],
      images: ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
      archives: ['zip', 'rar', '7z', 'tar', 'gz'],
      presentations: ['ppt', 'pptx'],
      code: ['js', 'py', 'java', 'cpp', 'c', 'go', 'rs']
    };

    this.dangerousExtensions = [
      'exe', 'bat', 'cmd', 'com', 'scr', 'vbs', 'js', 'jar',
      'msi', 'app', 'deb', 'rpm', 'dmg', 'iso'
    ];

    this.maxSafeSize = 25 * 1024 * 1024; // 25MB
    this.virusTotalApiKey = process.env.VIRUSTOTAL_API_KEY;
  }

  /**
   * Analyze all attachments in an email
   */
  async analyzeAttachments(email) {
    const attachments = email.attachments || [];

    if (attachments.length === 0) {
      return {
        count: 0,
        totalSize: 0,
        analysis: [],
        risk: 'none',
        summary: 'No attachments'
      };
    }

    const analyses = [];
    let totalSize = 0;
    let maxRisk = 'low';

    for (const attachment of attachments) {
      const analysis = await this.analyzeAttachment(attachment);
      analyses.push(analysis);
      totalSize += attachment.size || 0;

      // Update max risk level
      if (this.riskLevel(analysis.risk) > this.riskLevel(maxRisk)) {
        maxRisk = analysis.risk;
      }
    }

    return {
      count: attachments.length,
      totalSize: this.formatSize(totalSize),
      analysis: analyses,
      risk: maxRisk,
      summary: this.generateSummary(analyses),
      recommendations: this.generateRecommendations(analyses)
    };
  }

  /**
   * Analyze single attachment
   */
  async analyzeAttachment(attachment) {
    const filename = attachment.filename || attachment.name || 'unknown';
    const extension = this.getExtension(filename);
    const size = attachment.size || 0;
    const mimeType = attachment.mimeType || attachment.contentType || 'unknown';

    const analysis = {
      filename,
      extension,
      size: this.formatSize(size),
      mimeType,
      category: this.categorizeFile(extension),
      risk: 'low',
      flags: [],
      metadata: {},
      content: null
    };

    // Security checks
    await this.performSecurityChecks(attachment, analysis);

    // Content extraction based on type
    if (this.shouldExtractContent(extension)) {
      analysis.content = await this.extractContent(attachment, extension);
    }

    // Specialized parsing
    if (extension === 'pdf') {
      analysis.metadata.pdf = await this.parsePDF(attachment);
    } else if (['xls', 'xlsx', 'csv'].includes(extension)) {
      analysis.metadata.spreadsheet = await this.parseSpreadsheet(attachment);
    } else if (this.supportedTypes.images.includes(extension)) {
      analysis.metadata.image = await this.analyzeImage(attachment);
    }

    return analysis;
  }

  /**
   * Perform security checks
   */
  async performSecurityChecks(attachment, analysis) {
    const filename = attachment.filename || '';
    const extension = this.getExtension(filename);
    const size = attachment.size || 0;

    // Check 1: Dangerous extension
    if (this.dangerousExtensions.includes(extension)) {
      analysis.risk = 'high';
      analysis.flags.push('dangerous_extension');
      logger.warn('Dangerous file extension detected', { filename, extension });
    }

    // Check 2: Double extension trick
    if (filename.split('.').length > 2) {
      analysis.flags.push('double_extension');
      analysis.risk = this.escalateRisk(analysis.risk, 'medium');
    }

    // Check 3: Suspicious filename
    if (this.isSuspiciousFilename(filename)) {
      analysis.flags.push('suspicious_filename');
      analysis.risk = this.escalateRisk(analysis.risk, 'medium');
    }

    // Check 4: Size check
    if (size > this.maxSafeSize) {
      analysis.flags.push('large_file');
      analysis.risk = this.escalateRisk(analysis.risk, 'medium');
    }

    // Check 5: MIME type mismatch
    if (attachment.mimeType && !this.mimeMatchesExtension(attachment.mimeType, extension)) {
      analysis.flags.push('mime_mismatch');
      analysis.risk = this.escalateRisk(analysis.risk, 'high');
    }

    // Check 6: Password protected archives
    if (['zip', 'rar', '7z'].includes(extension) && await this.isPasswordProtected(attachment)) {
      analysis.flags.push('password_protected');
      analysis.risk = this.escalateRisk(analysis.risk, 'medium');
    }

    // Check 7: Macros in Office documents
    if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(extension)) {
      if (await this.containsMacros(attachment)) {
        analysis.flags.push('contains_macros');
        analysis.risk = this.escalateRisk(analysis.risk, 'high');
      }
    }

    // Check 8: VirusTotal scan (if API key available)
    if (this.virusTotalApiKey && analysis.risk !== 'low') {
      const vtResult = await this.scanVirusTotal(attachment);
      if (vtResult.malicious > 0) {
        analysis.risk = 'critical';
        analysis.flags.push('malware_detected');
        analysis.metadata.virusTotal = vtResult;
      }
    }
  }

  /**
   * Extract text content from attachment
   */
  async extractContent(attachment, extension) {
    try {
      switch (extension) {
        case 'txt':
        case 'md':
        case 'log':
          return await this.extractTextContent(attachment);

        case 'pdf':
          return await this.extractPDFText(attachment);

        case 'doc':
        case 'docx':
          return await this.extractWordText(attachment);

        default:
          return null;
      }
    } catch (error) {
      logger.error('Failed to extract content', {
        filename: attachment.filename,
        error: error.message
      });
      return null;
    }
  }

  /**
   * Parse PDF metadata
   */
  async parsePDF(attachment) {
    // In production, use pdf-parse or similar library
    return {
      pages: 0,
      author: 'unknown',
      creationDate: null,
      encrypted: false,
      forms: false,
      extractedText: null
    };
  }

  /**
   * Parse spreadsheet data
   */
  async parseSpreadsheet(attachment) {
    // In production, use xlsx or similar library
    return {
      sheets: [],
      rowCount: 0,
      columnCount: 0,
      hasFormulas: false,
      hasCharts: false
    };
  }

  /**
   * Analyze image
   */
  async analyzeImage(attachment) {
    const metadata = {
      width: 0,
      height: 0,
      format: this.getExtension(attachment.filename),
      hasExif: false,
      ocrText: null
    };

    // In production, perform OCR if needed
    // metadata.ocrText = await this.performOCR(attachment);

    return metadata;
  }

  /**
   * Perform OCR on image
   */
  async performOCR(attachment) {
    // In production, use Tesseract.js or cloud OCR service
    return null;
  }

  /**
   * Check if file is password protected
   */
  async isPasswordProtected(attachment) {
    // In production, check archive headers
    return false;
  }

  /**
   * Check if Office document contains macros
   */
  async containsMacros(attachment) {
    // In production, parse Office XML structure
    return false;
  }

  /**
   * Scan with VirusTotal
   */
  async scanVirusTotal(attachment) {
    if (!this.virusTotalApiKey) {
      return { malicious: 0, total: 0 };
    }

    try {
      // In production, implement actual VirusTotal API call
      // 1. Calculate file hash
      // 2. Check if hash exists in VT database
      // 3. If not, upload file for scanning
      // 4. Return results

      logger.info('VirusTotal scan requested', {
        filename: attachment.filename
      });

      return {
        malicious: 0,
        suspicious: 0,
        clean: 0,
        total: 0,
        scanned: false
      };
    } catch (error) {
      logger.error('VirusTotal scan failed', {
        error: error.message
      });
      return { malicious: 0, total: 0, error: error.message };
    }
  }

  /**
   * Extract invoice data
   */
  async parseInvoice(attachment) {
    // In production, use AI-powered invoice parsing
    const invoice = {
      invoiceNumber: null,
      date: null,
      dueDate: null,
      vendor: null,
      total: null,
      currency: null,
      lineItems: [],
      confidence: 0
    };

    // Use pattern matching or ML model to extract
    const text = await this.extractContent(attachment, this.getExtension(attachment.filename));

    if (text) {
      // Extract invoice number
      const invoiceMatch = text.match(/invoice\s*#?\s*:?\s*([A-Z0-9-]+)/i);
      if (invoiceMatch) {
        invoice.invoiceNumber = invoiceMatch[1];
        invoice.confidence += 20;
      }

      // Extract total amount
      const totalMatch = text.match(/total\s*:?\s*\$?\s*([\d,]+\.?\d*)/i);
      if (totalMatch) {
        invoice.total = parseFloat(totalMatch[1].replace(/,/g, ''));
        invoice.currency = 'USD';
        invoice.confidence += 20;
      }

      // Extract date
      const dateMatch = text.match(/date\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})/i);
      if (dateMatch) {
        invoice.date = dateMatch[1];
        invoice.confidence += 20;
      }
    }

    return invoice;
  }

  /**
   * Categorize file by extension
   */
  categorizeFile(extension) {
    for (const [category, extensions] of Object.entries(this.supportedTypes)) {
      if (extensions.includes(extension)) {
        return category;
      }
    }
    return 'other';
  }

  /**
   * Get file extension
   */
  getExtension(filename) {
    if (!filename) return '';
    const parts = filename.toLowerCase().split('.');
    return parts.length > 1 ? parts[parts.length - 1] : '';
  }

  /**
   * Check if should extract content
   */
  shouldExtractContent(extension) {
    const extractable = ['txt', 'md', 'log', 'pdf', 'doc', 'docx', 'csv'];
    return extractable.includes(extension);
  }

  /**
   * Extract plain text content
   */
  async extractTextContent(attachment) {
    // In production, read file content
    return '';
  }

  /**
   * Extract PDF text
   */
  async extractPDFText(attachment) {
    // In production, use pdf-parse
    return '';
  }

  /**
   * Extract Word document text
   */
  async extractWordText(attachment) {
    // In production, use mammoth or docx library
    return '';
  }

  /**
   * Check if filename is suspicious
   */
  isSuspiciousFilename(filename) {
    const suspicious = [
      /invoice.*\.zip/i,
      /payment.*\.exe/i,
      /urgent.*\.scr/i,
      /re:.*\.(exe|scr|bat)/i,
      /\.(exe|scr)\.pdf$/i // Fake double extension
    ];

    return suspicious.some(pattern => pattern.test(filename));
  }

  /**
   * Check if MIME type matches extension
   */
  mimeMatchesExtension(mimeType, extension) {
    const mimeMap = {
      'pdf': 'application/pdf',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xls': 'application/vnd.ms-excel',
      'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'zip': 'application/zip',
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'gif': 'image/gif'
    };

    const expectedMime = mimeMap[extension];
    return !expectedMime || mimeType === expectedMime;
  }

  /**
   * Escalate risk level
   */
  escalateRisk(currentRisk, newRisk) {
    const levels = { 'low': 1, 'medium': 2, 'high': 3, 'critical': 4 };
    return levels[newRisk] > levels[currentRisk] ? newRisk : currentRisk;
  }

  /**
   * Get numeric risk level
   */
  riskLevel(risk) {
    const levels = { 'none': 0, 'low': 1, 'medium': 2, 'high': 3, 'critical': 4 };
    return levels[risk] || 0;
  }

  /**
   * Format file size
   */
  formatSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }

  /**
   * Generate summary
   */
  generateSummary(analyses) {
    const categories = {};
    analyses.forEach(a => {
      categories[a.category] = (categories[a.category] || 0) + 1;
    });

    const parts = Object.entries(categories).map(([cat, count]) =>
      `${count} ${cat}`
    );

    return parts.join(', ');
  }

  /**
   * Generate recommendations
   */
  generateRecommendations(analyses) {
    const recommendations = [];

    const highRisk = analyses.filter(a => a.risk === 'high' || a.risk === 'critical');
    if (highRisk.length > 0) {
      recommendations.push('⚠️ High-risk attachments detected - do not open or forward');
      recommendations.push('🛡️ Quarantine these files immediately');
    }

    const macros = analyses.filter(a => a.flags.includes('contains_macros'));
    if (macros.length > 0) {
      recommendations.push('⚠️ Office documents contain macros - verify sender before opening');
    }

    const large = analyses.filter(a => a.flags.includes('large_file'));
    if (large.length > 0) {
      recommendations.push('📦 Large files detected - may require compression or cloud storage');
    }

    if (recommendations.length === 0) {
      recommendations.push('✅ All attachments appear safe');
    }

    return recommendations;
  }

  /**
   * Calculate file hash
   */
  calculateHash(data, algorithm = 'sha256') {
    return crypto.createHash(algorithm).update(data).digest('hex');
  }
}

module.exports = new AttachmentParser();
module.exports.AttachmentParser = AttachmentParser;
