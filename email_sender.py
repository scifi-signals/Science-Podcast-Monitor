# email_sender.py
# Email delivery for Science Trend Monitor digests
# Uses Gmail REST API (works on DigitalOcean where SMTP ports are blocked)

import base64
import os
import re
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')


def load_email_config():
    """Load email configuration from email_config.json or environment variables."""
    config_path = os.path.join(os.path.dirname(__file__), 'email_config.json')

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
            return {
                'sender_email': file_config.get('sender', {}).get('email', ''),
                'sender_name': file_config.get('sender', {}).get('name', 'Science Trend Monitor'),
                'recipients': file_config.get('recipients', []),
            }
        except Exception:
            pass

    return {
        'sender_email': os.environ.get('STM_SENDER_EMAIL', ''),
        'sender_name': os.environ.get('STM_SENDER_NAME', 'Science Trend Monitor'),
        'recipients': [r for r in os.environ.get('STM_RECIPIENTS', '').split(',') if r],
    }


EMAIL_CONFIG = load_email_config()


def _get_gmail_service():
    """Get an authenticated Gmail API service instance."""
    if not GMAIL_API_AVAILABLE:
        return None, "Gmail API libraries not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib"

    if not os.path.exists(TOKEN_FILE):
        return None, f"OAuth token not found at {TOKEN_FILE}. Run: python gmail_auth.py"

    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception as e:
        return None, f"Failed to load token: {e}"

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
        except Exception as e:
            return None, f"Failed to refresh token: {e}. Re-run: python gmail_auth.py"

    if not creds.valid:
        return None, "Token is invalid. Re-run: python gmail_auth.py"

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service, None
    except Exception as e:
        return None, f"Failed to build Gmail service: {e}"


def _send_via_gmail(message):
    """Send a MIMEMultipart message via Gmail REST API."""
    service, error = _get_gmail_service()
    if error:
        return {'success': False, 'message': error}

    try:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': f"Gmail API error: {e}"}


def html_to_plain_text(html_content):
    """Convert HTML to plain text for email clients that don't support HTML."""
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'\n=== \1 ===\n', text)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n--- \1 ---\n', text)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n\1\n', text)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n\1\n', text)
    text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', text)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'  - \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<div[^>]*>', '\n', text)
    text = re.sub(r'</div>', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    return text.strip()


def send_digest_email(html_file_path, subject=None, recipients=None, config=None):
    """
    Send the digest HTML file via email.

    Args:
        html_file_path: Path to the generated HTML digest file
        subject: Email subject (default: auto-generated with date)
        recipients: List of email addresses (default: from config)
        config: Email configuration dict (default: EMAIL_CONFIG)

    Returns:
        dict with 'success' bool and 'message' string
    """
    if config is None:
        config = EMAIL_CONFIG

    if recipients is None:
        recipients = [r.strip() for r in config.get('recipients', []) if r.strip()]

    if not recipients:
        return {
            'success': False,
            'message': 'No recipients configured. Add recipients to email_config.json.'
        }

    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        return {
            'success': False,
            'message': f'Digest file not found: {html_file_path}'
        }

    if subject is None:
        today = datetime.now().strftime('%B %d, %Y')
        subject = f'Science Trend Monitor - {today}'

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = f"{config.get('sender_name', 'Science Trend Monitor')} <{config['sender_email']}>"
    message['To'] = ', '.join(recipients)

    plain_text = html_to_plain_text(html_content)
    message.attach(MIMEText(plain_text, 'plain'))
    message.attach(MIMEText(html_content, 'html'))

    result = _send_via_gmail(message)
    if result['success']:
        return {
            'success': True,
            'message': f'Digest sent to {len(recipients)} recipient(s): {", ".join(recipients)}'
        }
    return result


def send_spike_alert_email(spikes, digest_url=None, recipients=None, config=None):
    """
    Send an immediate email alert when spikes are detected.

    Args:
        spikes: List of spike dicts from spike_detector
        digest_url: Optional URL to the full digest
        recipients: List of email addresses (default: from config)
        config: Email configuration dict (default: EMAIL_CONFIG)

    Returns:
        dict with 'success' bool and 'message' string
    """
    if config is None:
        config = EMAIL_CONFIG

    if not spikes:
        return {'success': True, 'message': 'No spikes to report'}

    if recipients is None:
        recipients = [r.strip() for r in config.get('recipients', []) if r.strip()]

    if not recipients:
        return {
            'success': False,
            'message': 'No recipients configured for spike alerts'
        }

    today = datetime.now().strftime('%B %d, %Y')
    subject = f'[SPIKE ALERT] Science Trend Monitor - {len(spikes)} unusual topic(s) detected'

    spike_items_html = ""
    spike_items_text = ""

    for spike in spikes:
        spike_type = "COVERAGE SURGE" if spike.get('spike_type') == 'surge' else "NEW MAJOR TOPIC"
        color = "#c53030" if spike.get('spike_type') == 'surge' else "#dd6b20"
        sources_str = ", ".join(spike.get('sources', [])[:5])

        spike_items_html += f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid {color};">
            <span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold;">{spike_type}</span>
            <h3 style="color:#1a365d;margin:8px 0;font-size:18px;">{spike['topic']}</h3>
            <p style="color:#4a5568;margin:4px 0;"><strong>{spike['source_count']} sources</strong> (baseline: {spike['baseline']})</p>
            <p style="color:#718096;font-size:14px;">Covered by: {sources_str}</p>
        </div>
"""
        spike_items_text += f"""
  [{spike_type}] {spike['topic']}
    - {spike['source_count']} sources (baseline: {spike['baseline']})
    - Covered by: {sources_str}
"""

    digest_link_html = ""
    digest_link_text = ""
    if digest_url:
        digest_link_html = f'<p style="margin-top:20px;"><a href="{digest_url}" style="background:#2b6cb0;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;">View Full Digest</a></p>'
        digest_link_text = f"\nView full digest: {digest_url}\n"

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f7fa; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg, #c53030 0%, #9b2c2c 100%); color:white; padding:24px; text-align:center;">
            <h1 style="margin:0; font-size:24px;">Spike Alert</h1>
            <p style="margin:8px 0 0 0; opacity:0.9;">Science Trend Monitor - {today}</p>
        </div>
        <div style="padding:24px;">
            <p style="color:#742a2a; font-size:16px; margin-bottom:20px;">
                <strong>{len(spikes)} topic(s)</strong> with unusual activity detected. These topics have significantly more coverage than their recent baseline.
            </p>
            {spike_items_html}
            {digest_link_html}
        </div>
        <div style="background:#f8fafc; padding:16px; text-align:center; color:#718096; font-size:12px;">
            Science Trend Monitor | National Academies of Sciences, Engineering, and Medicine
        </div>
    </div>
</body>
</html>
"""

    plain_text = f"""
SPIKE ALERT - Science Trend Monitor
{today}

{len(spikes)} topic(s) with unusual activity detected:
{spike_items_text}
{digest_link_text}
---
Science Trend Monitor | NASEM
"""

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = f"{config.get('sender_name', 'Science Trend Monitor')} <{config['sender_email']}>"
    message['To'] = ', '.join(recipients)

    message.attach(MIMEText(plain_text, 'plain'))
    message.attach(MIMEText(html_content, 'html'))

    result = _send_via_gmail(message)
    if result['success']:
        return {
            'success': True,
            'message': f'Spike alert sent to {len(recipients)} recipient(s)'
        }
    return result


def send_test_email(recipient=None, config=None):
    """Send a test email to verify configuration."""
    if config is None:
        config = EMAIL_CONFIG

    if recipient is None:
        recipients = [r.strip() for r in config.get('recipients', []) if r.strip()]
        if not recipients:
            return {'success': False, 'message': 'No recipient specified'}
        recipient = recipients[0]

    message = MIMEMultipart('alternative')
    message['Subject'] = 'Science Trend Monitor - Test Email'
    message['From'] = f"{config.get('sender_name', 'Science Trend Monitor')} <{config['sender_email']}>"
    message['To'] = recipient

    plain_text = f"""
Science Trend Monitor - Test Email

This is a test email from the Science Trend Monitor.
If you received this, your Gmail API configuration is working correctly.

Sender: {config.get('sender_email', 'unknown')}
Method: Gmail REST API

You can now run the full digest with email delivery.
"""

    html_content = f"""
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1a365d;">Science Trend Monitor</h1>
    <h2 style="color: #2d3748;">Test Email</h2>
    <p>This is a test email from the Science Trend Monitor.</p>
    <p style="color: #38a169; font-weight: bold;">If you received this, your Gmail API configuration is working correctly.</p>
    <hr style="border: 1px solid #e2e8f0;">
    <p style="color: #718096; font-size: 0.9em;">
        <strong>Configuration:</strong><br>
        Sender: {config.get('sender_email', 'unknown')}<br>
        Method: Gmail REST API
    </p>
</body>
</html>
"""

    message.attach(MIMEText(plain_text, 'plain'))
    message.attach(MIMEText(html_content, 'html'))

    result = _send_via_gmail(message)
    if result['success']:
        return {
            'success': True,
            'message': f'Test email sent to {recipient}'
        }
    return result


def check_email_config():
    """Check if email is properly configured."""
    issues = []

    if not GMAIL_API_AVAILABLE:
        issues.append('Gmail API libraries not installed (pip install google-api-python-client google-auth google-auth-oauthlib)')

    if not os.path.exists(TOKEN_FILE):
        issues.append(f'OAuth token not found ({TOKEN_FILE}). Run: python gmail_auth.py')

    if not os.path.exists(CREDENTIALS_FILE):
        issues.append(f'OAuth credentials not found ({CREDENTIALS_FILE}). Download from Google Cloud Console.')

    recipients = [r.strip() for r in EMAIL_CONFIG.get('recipients', []) if r.strip()]
    if not recipients:
        issues.append('No recipients configured in email_config.json')

    if issues:
        return {
            'configured': False,
            'issues': issues,
            'message': 'Email not fully configured:\n' + '\n'.join(f'  - {i}' for i in issues)
        }

    # Try loading the token to verify it's valid
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
    except Exception as e:
        return {
            'configured': False,
            'issues': [f'Token error: {e}'],
            'message': f'Token error: {e}. Re-run: python gmail_auth.py'
        }

    return {
        'configured': True,
        'issues': [],
        'message': f'Email configured (Gmail API): {EMAIL_CONFIG["sender_email"]} -> {", ".join(recipients)}'
    }


def print_setup_instructions():
    """Print instructions for setting up email delivery."""
    print("""
============================================================
EMAIL DELIVERY SETUP (Gmail REST API)
============================================================

This uses the Gmail REST API instead of SMTP, which works on
servers where SMTP ports (25, 465, 587) are blocked.

STEP 1: CREATE GOOGLE CLOUD CREDENTIALS
----------------------------------------
1. Go to https://console.cloud.google.com
2. Create a new project (or select existing)
3. Enable the Gmail API:
   - APIs & Services > Enable APIs & Services
   - Search for "Gmail API" > Enable
4. Configure OAuth consent screen:
   - APIs & Services > OAuth consent screen
   - User Type: External > Create
   - Fill in app name: "Science Trend Monitor"
   - Add your email as test user
5. Create credentials:
   - APIs & Services > Credentials
   - Create Credentials > OAuth client ID
   - Application type: Desktop app
   - Name: Science Trend Monitor
6. Download the JSON file
7. Save it as 'credentials.json' in this folder

STEP 2: AUTHORIZE THE APP
--------------------------
  python gmail_auth.py

This opens a browser window. Sign in with the Gmail account
you want to send from and click "Allow".

STEP 3: UPLOAD TO SERVER
-------------------------
  scp token.json credentials.json science-intel:/root/science-trend-monitor/

STEP 4: TEST IT
---------------
  python main.py --test-email

STEP 5: SEND A DIGEST
----------------------
  python main.py --email         (generate new + send)
  python main.py --send-last     (send most recent digest)

============================================================
""")


if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        print("Checking email configuration...")
        status = check_email_config()

        if not status['configured']:
            print(f"\n[!] {status['message']}")
            print_setup_instructions()
        else:
            print(f"[OK] {status['message']}")
            print("\nSending test email...")
            result = send_test_email()
            if result['success']:
                print(f"[OK] {result['message']}")
            else:
                print(f"[!] {result['message']}")

    elif '--setup' in sys.argv:
        print_setup_instructions()

    else:
        status = check_email_config()
        print("Email Configuration Status:")
        if status['configured']:
            print(f"  [OK] {status['message']}")
        else:
            print(f"  [!] Not configured")
            print("\nRun 'python email_sender.py --setup' for setup instructions")
            print("Run 'python email_sender.py --test' to test configuration")
