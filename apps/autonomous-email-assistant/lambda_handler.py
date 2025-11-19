#!/usr/bin/env python3
"""
AWS Lambda handler for autonomous email management.
Runs Claude Code with Gmail MCP to process emails hourly.
"""

import os
import json
import subprocess
import base64
from datetime import datetime
import pytz


def handler(event, context):
    """
    Lambda handler for email processing.

    Args:
        event: Lambda event (from EventBridge scheduler)
        context: Lambda context

    Returns:
        dict: Status response
    """
    print("=== Email Assistant Lambda Starting ===")
    print(f"Event: {json.dumps(event)}")

    # Setup Gmail MCP credentials from environment variables
    setup_gmail_mcp()

    # Setup Claude Code MCP configuration
    setup_claude_mcp_config()

    # Determine execution mode based on EST time
    execution_mode, current_hour = get_execution_mode()

    print(f"Execution Mode: {execution_mode}")
    print(f"Current Hour (EST): {current_hour}")

    # Run Claude Code with email processing prompt
    result = run_email_processing(execution_mode, current_hour)

    print("=== Email Assistant Lambda Completed ===")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Email processing completed',
            'execution_mode': execution_mode,
            'current_hour': current_hour,
            'result': result
        })
    }


def setup_gmail_mcp():
    """Decode and setup Gmail MCP credentials from environment variables."""
    print("Setting up Gmail MCP credentials...")

    gmail_mcp_dir = "/root/.gmail-mcp"
    os.makedirs(gmail_mcp_dir, exist_ok=True)

    # Decode base64-encoded credentials
    gmail_oauth_creds = os.environ.get('GMAIL_OAUTH_CREDENTIALS', '')
    gmail_creds = os.environ.get('GMAIL_CREDENTIALS', '')

    if not gmail_oauth_creds or not gmail_creds:
        raise ValueError("Missing Gmail credentials in environment variables")

    # Decode and write credentials
    with open(f"{gmail_mcp_dir}/gcp-oauth.keys.json", 'w') as f:
        f.write(base64.b64decode(gmail_oauth_creds).decode('utf-8'))

    with open(f"{gmail_mcp_dir}/credentials.json", 'w') as f:
        f.write(base64.b64decode(gmail_creds).decode('utf-8'))

    print("✓ Gmail MCP credentials configured")


def setup_claude_mcp_config():
    """Setup Claude Code MCP configuration."""
    print("Setting up Claude MCP configuration...")

    config_dir = "/root/.config/claude"
    os.makedirs(config_dir, exist_ok=True)

    mcp_config = {
        "mcpServers": {
            "gmail": {
                "type": "stdio",
                "command": "npx",
                "args": ["@gongrzhe/server-gmail-autoauth-mcp"],
                "env": {}
            }
        }
    }

    with open(f"{config_dir}/claude_code_config.json", 'w') as f:
        json.dump(mcp_config, f, indent=2)

    print("✓ Claude MCP configuration created")


def get_execution_mode():
    """Determine execution mode based on EST time."""
    est = pytz.timezone('America/New_York')
    now = datetime.now(est)
    hour = now.hour

    if hour == 7:
        return "morning_brief", hour
    elif hour == 17:
        return "eod_report", hour
    elif hour == 13:
        return "midday_check", hour
    else:
        return "hourly_process", hour


def run_email_processing(execution_mode, current_hour):
    """Run Claude Code to process emails."""
    print("Running Claude Code email processing...")

    # Get environment variables
    claude_token = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')
    escalation_phone = os.environ.get('ESCALATION_PHONE', '+14077448449')
    test_mode = os.environ.get('TEST_MODE', 'false')

    if not claude_token:
        raise ValueError("Missing CLAUDE_CODE_OAUTH_TOKEN environment variable")

    # Email processing prompt (from workflow YAML)
    prompt = get_email_processing_prompt(execution_mode, current_hour, test_mode)

    # Run Claude Code
    env = os.environ.copy()
    env['CLAUDE_CODE_OAUTH_TOKEN'] = claude_token
    env['EXECUTION_MODE'] = execution_mode
    env['CURRENT_HOUR'] = str(current_hour)
    env['ESCALATION_PHONE'] = escalation_phone
    env['TEST_MODE'] = test_mode

    try:
        result = subprocess.run(
            ['claude', '--print', '--dangerously-skip-permissions', '--mcp-config', '/root/.config/claude/claude_code_config.json'],
            input=prompt.encode('utf-8'),
            capture_output=True,
            timeout=540,  # 9 minutes
            env=env
        )

        output = result.stdout.decode('utf-8')
        errors = result.stderr.decode('utf-8')

        print("=== Claude Code Output ===")
        print(output)

        if errors:
            print("=== Claude Code Errors ===")
            print(errors)

        if result.returncode != 0:
            raise RuntimeError(f"Claude Code failed with exit code {result.returncode}")

        return {
            'success': True,
            'output': output[:1000]  # Truncate for Lambda response
        }

    except subprocess.TimeoutExpired:
        print("ERROR: Claude Code execution timed out")
        raise
    except Exception as e:
        print(f"ERROR: Claude Code execution failed: {str(e)}")
        raise


def get_email_processing_prompt(execution_mode, current_hour, test_mode):
    """Generate the email processing prompt."""
    return f"""You are Terrance Brandon's Executive Email Assistant, running autonomous hourly email management.

CURRENT CONTEXT:
- Execution Mode: {execution_mode}
- Current Hour (EST): {current_hour}:00
- Test Mode: {test_mode}

YOUR CONFIGURATION (from claude-agents/executive-email-assistant-config-terrance.md):
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

LABELS SYSTEM:
1. Action Required - High-priority items needing decision
2. To Read - Information to review later
3. Waiting For - Awaiting external responses
4. Completed - Finished items
5. VIP - VIP contacts and always-escalate list
6. Meetings - Calendar/scheduling
7. Travel - Travel related
8. Expenses - Receipts, invoices
9. Newsletters - Subscriptions

TIER CLASSIFICATION:

TIER 1 (Escalate Immediately - SMS + Priority Email):
- Revenue-impacting emails from customers/prospects
- Strategic partnership opportunities
- Major donor communications
- Speaking/media opportunities
- Financial matters requiring approval
- Employee/HR issues
- Legal matters
- Emails from off-limits contacts
- Anything marked urgent/confidential

TIER 2 (Handle Independently):
- Meeting scheduling
- Newsletter subscriptions
- Vendor communications (routine)
- Follow-up reminders
- Information requests
- Administrative tasks
- Travel confirmations
- Expense receipts

TIER 3 (Draft for Approval):
- Meeting decline requests
- Strategic communications
- First-time contacts (seemingly important)
- Requires Terrance's expertise/voice

TIER 4 (Draft-Only, Never Send):
- HR/Employee performance matters
- Financial negotiations
- Legal matters
- Board communications
- Personal matters (health, family)

YOUR TASKS FOR THIS HOUR:

1. ACCESS GMAIL VIA MCP
   - Connect to terrance@goodportion.org inbox
   - Use Gmail MCP tools (should be available)

2. FETCH NEW EMAILS
   - Get emails received in the last hour
   - If this is first run today (7 AM), get overnight emails since 5 PM yesterday

3. PROCESS EACH EMAIL:
   - Read sender, subject, and content
   - Classify into Tier 1/2/3/4
   - Apply appropriate Gmail label
   - Take action based on tier

4. GENERATE OUTPUT BASED ON MODE:
   - morning_brief (7 AM): Comprehensive morning brief
   - eod_report (5 PM): End-of-day report
   - midday_check (1 PM): Only if Tier 1 urgent items exist
   - hourly_process: Silent processing, SMS for Tier 1 only

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

## ESCALATIONS
[If any Tier 1 items, list them]

## MODE-SPECIFIC OUTPUT
[Morning brief / EOD report / Midday alert / Silent processing confirmation]
"""
