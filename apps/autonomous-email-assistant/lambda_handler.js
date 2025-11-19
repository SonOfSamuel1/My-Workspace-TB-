/**
 * AWS Lambda handler for autonomous email management.
 * Runs Claude Code with Gmail MCP to process emails hourly.
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

exports.handler = async (event, context) => {
    console.log('=== Email Assistant Lambda Starting ===');
    console.log('Event:', JSON.stringify(event));

    try {
        // Setup Gmail MCP credentials
        setupGmailMcp();

        // Setup Claude Code MCP configuration
        setupClaudeMcpConfig();

        // Determine execution mode based on EST time
        const { executionMode, currentHour } = getExecutionMode();
        console.log(`Execution Mode: ${executionMode}`);
        console.log(`Current Hour (EST): ${currentHour}`);

        // Run Claude Code with email processing prompt
        const result = runEmailProcessing(executionMode, currentHour);

        console.log('=== Email Assistant Lambda Completed ===');

        return {
            statusCode: 200,
            body: JSON.stringify({
                message: 'Email processing completed',
                execution_mode: executionMode,
                current_hour: currentHour,
                result: result
            })
        };
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({
                error: error.message,
                stack: error.stack
            })
        };
    }
};

function setupGmailMcp() {
    console.log('Setting up Gmail MCP credentials...');

    const gmailMcpDir = '/tmp/.gmail-mcp';
    if (!fs.existsSync(gmailMcpDir)) {
        fs.mkdirSync(gmailMcpDir, { recursive: true });
    }

    // Decode base64-encoded credentials
    const gmailOauthCreds = process.env.GMAIL_OAUTH_CREDENTIALS;
    const gmailCreds = process.env.GMAIL_CREDENTIALS;

    if (!gmailOauthCreds || !gmailCreds) {
        throw new Error('Missing Gmail credentials in environment variables');
    }

    // Decode and write credentials
    fs.writeFileSync(
        path.join(gmailMcpDir, 'gcp-oauth.keys.json'),
        Buffer.from(gmailOauthCreds, 'base64').toString('utf-8')
    );

    fs.writeFileSync(
        path.join(gmailMcpDir, 'credentials.json'),
        Buffer.from(gmailCreds, 'base64').toString('utf-8')
    );

    // Set environment variable for Gmail MCP
    process.env.HOME = '/tmp';

    console.log('✓ Gmail MCP credentials configured');
}

function setupClaudeMcpConfig() {
    console.log('Setting up Claude MCP configuration...');

    const configDir = '/tmp/.config/claude';
    if (!fs.existsSync(configDir)) {
        fs.mkdirSync(configDir, { recursive: true });
    }

    const mcpConfig = {
        mcpServers: {
            gmail: {
                type: 'stdio',
                command: 'npx',
                args: ['@gongrzhe/server-gmail-autoauth-mcp'],
                env: {}
            }
        }
    };

    fs.writeFileSync(
        path.join(configDir, 'claude_code_config.json'),
        JSON.stringify(mcpConfig, null, 2)
    );

    console.log('✓ Claude MCP configuration created');
}

function getExecutionMode() {
    const now = new Date();
    // Convert to EST
    const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const hour = estTime.getHours();

    let executionMode;
    if (hour === 7) {
        executionMode = 'morning_brief';
    } else if (hour === 17) {
        executionMode = 'eod_report';
    } else if (hour === 13) {
        executionMode = 'midday_check';
    } else {
        executionMode = 'hourly_process';
    }

    return { executionMode, currentHour: hour };
}

function runEmailProcessing(executionMode, currentHour) {
    console.log('Running Claude Code email processing...');

    const claudeToken = process.env.CLAUDE_CODE_OAUTH_TOKEN;
    const escalationPhone = process.env.ESCALATION_PHONE || '+14077448449';
    const testMode = process.env.TEST_MODE || 'false';

    if (!claudeToken) {
        throw new Error('Missing CLAUDE_CODE_OAUTH_TOKEN environment variable');
    }

    // Email processing prompt
    const prompt = getEmailProcessingPrompt(executionMode, currentHour, testMode);

    // Set environment variables
    process.env.CLAUDE_CODE_OAUTH_TOKEN = claudeToken;
    process.env.EXECUTION_MODE = executionMode;
    process.env.CURRENT_HOUR = String(currentHour);
    process.env.ESCALATION_PHONE = escalationPhone;
    process.env.TEST_MODE = testMode;

    try {
        const output = execSync(
            `claude --print --dangerously-skip-permissions --mcp-config /tmp/.config/claude/claude_code_config.json`,
            {
                input: prompt,
                encoding: 'utf-8',
                timeout: 540000, // 9 minutes
                maxBuffer: 10 * 1024 * 1024, // 10MB
                env: process.env
            }
        );

        console.log('=== Claude Code Output ===');
        console.log(output);

        return {
            success: true,
            output: output.substring(0, 1000) // Truncate for response
        };
    } catch (error) {
        console.error('Claude Code execution failed:', error.message);
        if (error.stdout) console.log('stdout:', error.stdout);
        if (error.stderr) console.error('stderr:', error.stderr);
        throw error;
    }
}

function getEmailProcessingPrompt(executionMode, currentHour, testMode) {
    return `You are Terrance Brandon's Executive Email Assistant, running autonomous hourly email management.

CURRENT CONTEXT:
- Execution Mode: ${executionMode}
- Current Hour (EST): ${currentHour}:00
- Test Mode: ${testMode}

YOUR CONFIGURATION:
- Email: terrance@goodportion.org
- Delegation Level: Level 2 (Manage)
- Time Zone: EST
- Communication Style: Casual (Hi/Thanks), "Kind regards,", NO emojis
- Escalation: SMS to 407-744-8449 for Tier 1 urgent

OFF-LIMITS CONTACTS (Always Escalate as Tier 1):
- Family Members
- Darrell Coleman
- Paul Robertson
- Tatyana Brandon

YOUR TASKS FOR THIS HOUR:

1. ACCESS GMAIL VIA MCP
   - Connect to terrance@goodportion.org inbox
   - Use Gmail MCP tools

2. FETCH NEW EMAILS
   - Get emails received in the last hour
   - If this is first run today (7 AM), get overnight emails since 5 PM yesterday

3. PROCESS EACH EMAIL:
   - Read sender, subject, and content
   - Classify into Tier 1/2/3/4
   - Apply appropriate Gmail label
   - Take action based on tier

4. GENERATE OUTPUT BASED ON MODE

BEGIN PROCESSING NOW.

## EMAIL PROCESSING SUMMARY
- Emails checked: [#]
- New emails found: [#]
- Tier 1 (escalated): [#]
- Tier 2 (handled): [#]
- Tier 3 (drafted): [#]
- Tier 4 (flagged): [#]

## ACTIONS TAKEN
[List each action taken]
`;
}
