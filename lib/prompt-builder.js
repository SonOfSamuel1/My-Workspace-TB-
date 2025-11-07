/**
 * Prompt Builder for Executive Email Assistant
 *
 * Generates Claude prompts from template and configuration.
 * Shared between GitHub Actions and AWS Lambda deployments.
 */

const fs = require('fs');
const path = require('path');

class PromptBuilder {
  constructor(configPath) {
    this.config = this.loadConfig(configPath);
    this.template = this.loadTemplate();
  }

  loadConfig(configPath) {
    // Load configuration from markdown file
    const configContent = fs.readFileSync(configPath, 'utf-8');

    // Parse configuration (simplified - you'd want more robust parsing)
    return {
      executiveName: this.extractField(configContent, 'Name'),
      executiveEmail: this.extractField(configContent, 'Email'),
      delegationLevel: this.extractField(configContent, 'Current Level'),
      timezone: this.extractField(configContent, 'Time Zone'),
      escalationPhone: this.extractField(configContent, 'Phone \\(Escalations\\)'),
      offLimitsContacts: this.extractList(configContent, 'Off-Limits Contacts'),
      communicationStyle: this.extractCommunicationStyle(configContent),
      labels: this.extractLabels(configContent),
      tierCriteria: this.extractTierCriteria(configContent),
      constraints: this.extractConstraints(configContent)
    };
  }

  loadTemplate() {
    const templatePath = path.join(__dirname, '..', 'prompts', 'email-processing-prompt.template.md');
    return fs.readFileSync(templatePath, 'utf-8');
  }

  extractField(content, fieldName) {
    const regex = new RegExp(`\\*\\*${fieldName}:\\*\\*\\s*(.+)`, 'i');
    const match = content.match(regex);
    return match ? match[1].trim() : '';
  }

  extractList(content, sectionName) {
    const regex = new RegExp(`### ${sectionName}[\\s\\S]*?(?=\\n###|\\n---|\$)`, 'i');
    const match = content.match(regex);
    if (!match) return [];

    const items = match[0].match(/^\d+\.\s+(.+)$/gm) || [];
    return items.map(item => item.replace(/^\d+\.\s+/, '').trim());
  }

  extractCommunicationStyle(content) {
    const greeting = this.extractField(content, 'Greeting');
    const closing = this.extractField(content, 'Closing');
    const emojis = this.extractField(content, 'Emojis');

    return `${greeting}, ${closing}, ${emojis}`;
  }

  extractLabels(content) {
    const labels = [];
    const labelRegex = /(\d+)\.\s+\*\*(.+?)\*\*\s+-\s+(.+)/g;
    let match;

    while ((match = labelRegex.exec(content)) !== null) {
      labels.push({
        index: match[1],
        name: match[2],
        description: match[3]
      });
    }

    return labels;
  }

  extractTierCriteria(content) {
    return {
      tier1: this.extractTierSection(content, 'TIER 1'),
      tier2: this.extractTierSection(content, 'TIER 2'),
      tier3: this.extractTierSection(content, 'TIER 3'),
      tier4: this.extractTierSection(content, 'TIER 4')
    };
  }

  extractTierSection(content, tierName) {
    const regex = new RegExp(`### ${tierName}[:\\s]+[\\s\\S]*?(?=\\n###|\\n---|\$)`, 'i');
    const match = content.match(regex);
    if (!match) return [];

    const items = match[0].match(/^\d+\.\s+(.+)$/gm) || [];
    return items.map(item => item.replace(/^\d+\.\s+/, '').trim());
  }

  extractConstraints(content) {
    const constraints = [];
    const constraintsSection = content.match(/IMPORTANT CONSTRAINTS[\\s\\S]*?(?=\\n##|\\n---|\$)/i);

    if (constraintsSection) {
      const items = constraintsSection[0].match(/^[-•]\s+(.+)$/gm) || [];
      return items.map(item => item.replace(/^[-•]\s+/, '').trim());
    }

    return [
      'Never use emojis',
      'Always identify as "Executive Email Assistant for ' + this.config.executiveName + '"',
      'Sign responses with "Kind regards,"',
      'If meeting decline needed, draft but don\'t send (Tier 3)',
      'Be conservative with escalations during learning phase'
    ];
  }

  getModeSpecificInstructions(mode) {
    const instructions = {
      morning_brief: `
IF MODE = "morning_brief" (7 AM):
- Generate comprehensive morning brief
- Include overnight email summary
- List all Tier 1 escalations
- List all Tier 3/4 items needing approval
- Show updated "Waiting For" status
- Send via email to ${this.config.executiveEmail}
- Subject: "Morning Brief - [Date]"
`,
      eod_report: `
IF MODE = "eod_report" (5 PM):
- Generate comprehensive end-of-day report
- Total emails processed today
- Actions taken (Tier 2 handled)
- Items awaiting approval (Tier 3/4)
- Still waiting for responses
- Tomorrow's priorities
- Send via email to ${this.config.executiveEmail}
- Subject: "End of Day Report - [Date]"
`,
      midday_check: `
IF MODE = "midday_check" (1 PM):
- Only send report if Tier 1 urgent items exist
- Brief summary of urgent matters
- Subject: "Midday Alert - Urgent Items"
`,
      hourly_process: `
IF MODE = "hourly_process":
- Process emails silently
- Only send SMS for Tier 1 urgent items
- No email report unless critical
`
    };

    return instructions[mode] || instructions.hourly_process;
  }

  build(executionMode, currentHour, testMode = false) {
    let prompt = this.template;

    // Replace simple variables
    const replacements = {
      '{{EXECUTIVE_NAME}}': this.config.executiveName || 'the Executive',
      '{{EXECUTIVE_EMAIL}}': this.config.executiveEmail,
      '{{EXECUTION_MODE}}': executionMode,
      '{{CURRENT_HOUR}}': currentHour,
      '{{TIMEZONE}}': this.config.timezone || 'EST',
      '{{TEST_MODE}}': testMode.toString(),
      '{{DELEGATION_LEVEL}}': this.config.delegationLevel || 'Level 2 (Manage)',
      '{{COMMUNICATION_STYLE}}': this.config.communicationStyle,
      '{{ESCALATION_PHONE}}': this.config.escalationPhone,
      '{{MODE_SPECIFIC_INSTRUCTIONS}}': this.getModeSpecificInstructions(executionMode)
    };

    for (const [key, value] of Object.entries(replacements)) {
      prompt = prompt.replace(new RegExp(key, 'g'), value);
    }

    // Replace lists
    prompt = this.replaceList(prompt, 'OFF_LIMITS_CONTACTS', this.config.offLimitsContacts);
    prompt = this.replaceList(prompt, 'TIER_1_CRITERIA', this.config.tierCriteria.tier1);
    prompt = this.replaceList(prompt, 'TIER_2_CRITERIA', this.config.tierCriteria.tier2);
    prompt = this.replaceList(prompt, 'TIER_3_CRITERIA', this.config.tierCriteria.tier3);
    prompt = this.replaceList(prompt, 'TIER_4_CRITERIA', this.config.tierCriteria.tier4);
    prompt = this.replaceList(prompt, 'CONSTRAINTS', this.config.constraints);

    // Replace labels (more complex)
    prompt = this.replaceLabels(prompt, this.config.labels);

    return prompt;
  }

  replaceList(template, listName, items) {
    const regex = new RegExp(`{{#${listName}}}[\\s\\S]*?{{/${listName}}}`, 'g');
    const listTemplate = template.match(regex);

    if (!listTemplate || !items || items.length === 0) {
      return template.replace(regex, items && items.length > 0 ? items.map(item => `- ${item}`).join('\n') : '- None specified');
    }

    const itemTemplate = listTemplate[0]
      .replace(`{{#${listName}}}`, '')
      .replace(`{{/${listName}}}`, '')
      .trim();

    const renderedItems = items.map(item => {
      return itemTemplate.replace(/{{\.}}/g, item);
    }).join('\n');

    return template.replace(regex, renderedItems);
  }

  replaceLabels(template, labels) {
    const regex = /{{#LABELS}}[\s\S]*?{{\/LABELS}}/g;
    const listTemplate = template.match(regex);

    if (!listTemplate || !labels || labels.length === 0) {
      return template.replace(regex, 'No labels configured');
    }

    const renderedLabels = labels.map(label => {
      return `${label.index}. ${label.name} - ${label.description}`;
    }).join('\n');

    return template.replace(regex, renderedLabels);
  }
}

// CLI usage
if (require.main === module) {
  const configPath = process.argv[2] || path.join(__dirname, '..', 'claude-agents', 'executive-email-assistant-config-terrance.md');
  const mode = process.argv[3] || 'hourly_process';
  const hour = process.argv[4] || new Date().getHours();

  const builder = new PromptBuilder(configPath);
  const prompt = builder.build(mode, hour, process.env.TEST_MODE === 'true');

  console.log(prompt);
}

module.exports = PromptBuilder;
