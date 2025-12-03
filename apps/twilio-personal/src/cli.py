#!/usr/bin/env python3
"""
Twilio CLI for Personal Use
Interactive command-line interface for Twilio operations
"""

import click
import json
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.twilio_client import TwilioPersonalClient
from src.config import ConfigManager

console = Console()


@click.group()
@click.pass_context
def cli(ctx):
    """Twilio Personal CLI - Manage your Twilio account from the command line"""
    try:
        ctx.obj = TwilioPersonalClient()
    except Exception as e:
        console.print(f"[red]Error initializing Twilio client: {e}[/red]")
        console.print("[yellow]Please check your .env configuration[/yellow]")
        sys.exit(1)


@cli.command()
@click.option('--to', '-t', required=True, help='Recipient phone number (E.164 format)')
@click.option('--body', '-b', required=True, help='Message body')
@click.option('--from', '-f', 'from_number', help='Sender number (uses default if not specified)')
@click.pass_context
def send(ctx, to, body, from_number):
    """Send an SMS message"""
    client = ctx.obj

    try:
        with console.status("[cyan]Sending SMS...[/cyan]"):
            result = client.send_sms(to=to, body=body, from_number=from_number)

        panel = Panel(
            f"[green]✓ Message sent successfully![/green]\n\n"
            f"[bold]SID:[/bold] {result['sid']}\n"
            f"[bold]To:[/bold] {result['to']}\n"
            f"[bold]From:[/bold] {result['from']}\n"
            f"[bold]Status:[/bold] {result['status']}",
            title="SMS Sent",
            border_style="green"
        )
        console.print(panel)
    except Exception as e:
        console.print(f"[red]Failed to send SMS: {e}[/red]")


@cli.command()
@click.option('--body', '-b', required=True, help='Message body')
@click.pass_context
def send_self(ctx, body):
    """Send an SMS to your personal number"""
    client = ctx.obj

    try:
        with console.status("[cyan]Sending SMS to self...[/cyan]"):
            result = client.send_to_self(body=body)

        panel = Panel(
            f"[green]✓ Message sent to personal number![/green]\n\n"
            f"[bold]SID:[/bold] {result['sid']}\n"
            f"[bold]To:[/bold] {result['to']}\n"
            f"[bold]Status:[/bold] {result['status']}",
            title="SMS Sent to Self",
            border_style="green"
        )
        console.print(panel)
    except Exception as e:
        console.print(f"[red]Failed to send SMS: {e}[/red]")


@cli.command()
@click.option('--limit', '-l', default=10, help='Number of messages to retrieve')
@click.option('--days', '-d', default=7, help='Messages from last N days')
@click.pass_context
def history(ctx, limit, days):
    """View message history"""
    client = ctx.obj

    try:
        date_filter = datetime.now() - timedelta(days=days)

        with console.status("[cyan]Retrieving message history...[/cyan]"):
            messages = client.get_message_history(
                limit=limit,
                date_sent_after=date_filter
            )

        if not messages:
            console.print("[yellow]No messages found[/yellow]")
            return

        table = Table(title=f"Message History (Last {days} days)")
        table.add_column("Date", style="cyan")
        table.add_column("Direction", style="magenta")
        table.add_column("From", style="green")
        table.add_column("To", style="blue")
        table.add_column("Body", style="white", max_width=40)
        table.add_column("Status", style="yellow")

        for msg in messages:
            date_str = msg['date_sent'][:16] if msg['date_sent'] else 'N/A'
            table.add_row(
                date_str,
                msg['direction'],
                msg['from'][-4:],  # Show last 4 digits
                msg['to'][-4:],    # Show last 4 digits
                msg['body'][:40] + '...' if len(msg['body']) > 40 else msg['body'],
                msg['status']
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to retrieve history: {e}[/red]")


@cli.command()
@click.pass_context
def numbers(ctx):
    """List all phone numbers on the account"""
    client = ctx.obj

    try:
        with console.status("[cyan]Retrieving phone numbers...[/cyan]"):
            numbers = client.get_phone_numbers()

        if not numbers:
            console.print("[yellow]No phone numbers found[/yellow]")
            return

        table = Table(title="Phone Numbers")
        table.add_column("Phone Number", style="cyan")
        table.add_column("Friendly Name", style="green")
        table.add_column("SMS", style="yellow")
        table.add_column("MMS", style="yellow")
        table.add_column("Voice", style="yellow")

        for num in numbers:
            table.add_row(
                num['phone_number'],
                num['friendly_name'] or 'N/A',
                "✓" if num['capabilities']['sms'] else "✗",
                "✓" if num['capabilities']['mms'] else "✗",
                "✓" if num['capabilities']['voice'] else "✗"
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to retrieve phone numbers: {e}[/red]")


@cli.command()
@click.pass_context
def verify(ctx):
    """Verify Twilio configuration"""
    client = ctx.obj

    try:
        with console.status("[cyan]Verifying configuration...[/cyan]"):
            results = client.verify_configuration()

        table = Table(title="Configuration Verification")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")

        checks = [
            ("Account Valid", results['account_valid']),
            ("Phone Number Valid", results['phone_number_valid']),
            ("Personal Number Set", results['personal_number_set']),
            ("Can Send SMS", results['can_send_sms'])
        ]

        for check, status in checks:
            status_text = "[green]✓ Passed[/green]" if status else "[red]✗ Failed[/red]"
            table.add_row(check, status_text)

        console.print(table)

        # Show configuration details
        config = client.config
        console.print("\n[bold]Current Configuration:[/bold]")
        console.print(f"  Account SID: {config.account_sid[:8]}...")
        console.print(f"  Phone Number: {config.phone_number or '[red]Not set[/red]'}")
        console.print(f"  Personal Number: {config.personal_number or '[red]Not set[/red]'}")
        console.print(f"  Email: {config.email}")

    except Exception as e:
        console.print(f"[red]Verification failed: {e}[/red]")


@cli.command()
@click.pass_context
def balance(ctx):
    """Check account balance and status"""
    client = ctx.obj

    try:
        with console.status("[cyan]Retrieving account information...[/cyan]"):
            account = client.get_account_balance()

        panel = Panel(
            f"[bold]Account Status:[/bold] {account['status']}\n"
            f"[bold]Account Type:[/bold] {account['type']}\n"
            f"[bold]Friendly Name:[/bold] {account['friendly_name']}\n"
            f"[bold]Created:[/bold] {account['date_created'][:10] if account['date_created'] else 'N/A'}",
            title="Account Information",
            border_style="cyan"
        )
        console.print(panel)
    except Exception as e:
        console.print(f"[red]Failed to retrieve account info: {e}[/red]")


@cli.command()
def setup():
    """Interactive setup wizard"""
    console.print(Panel("[bold]Twilio Personal Setup Wizard[/bold]", style="cyan"))

    # Check if .env exists
    env_path = Path(__file__).parent.parent / '.env'

    if env_path.exists():
        console.print("[yellow]⚠ .env file already exists[/yellow]")
        if not click.confirm("Do you want to overwrite it?"):
            return

    console.print("\n[bold]Please provide your Twilio credentials:[/bold]")
    console.print("[dim]You can find these in your Twilio Console at https://console.twilio.com[/dim]\n")

    # Collect credentials
    account_sid = click.prompt("Account SID")
    auth_token = click.prompt("Auth Token", hide_input=True)
    phone_number = click.prompt("Twilio Phone Number (E.164 format, e.g., +1234567890)", default="")
    personal_number = click.prompt("Your Personal Number (for receiving notifications)", default="")

    # Write .env file
    env_content = f"""# Twilio Configuration
# Generated by Twilio Personal CLI

TWILIO_ACCOUNT_SID={account_sid}
TWILIO_AUTH_TOKEN={auth_token}
TWILIO_PHONE_NUMBER={phone_number}
MY_PERSONAL_NUMBER={personal_number}
TWILIO_EMAIL=twilio.everglade@mymailgpt.com
"""

    env_path.write_text(env_content)
    console.print(f"\n[green]✓ Configuration saved to {env_path}[/green]")

    # Test configuration
    if click.confirm("\nWould you like to verify your configuration?"):
        try:
            client = TwilioPersonalClient()
            results = client.verify_configuration()

            if all(results.values()):
                console.print("[green]✓ All checks passed! Your Twilio setup is complete.[/green]")
            else:
                console.print("[yellow]⚠ Some checks failed. Please review your configuration.[/yellow]")
        except Exception as e:
            console.print(f"[red]Configuration test failed: {e}[/red]")


if __name__ == '__main__':
    cli()