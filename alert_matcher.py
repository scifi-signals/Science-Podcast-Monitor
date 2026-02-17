# alert_matcher.py
# Match new episode topics against subscriber keyword subscriptions
# and send targeted alert emails

import os
import json
from datetime import datetime


SUBSCRIPTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alert_subscriptions.json')


def load_subscriptions():
    """Load subscriber data from alert_subscriptions.json."""
    if not os.path.exists(SUBSCRIPTIONS_FILE):
        return []

    try:
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('subscribers', [])
    except (json.JSONDecodeError, IOError):
        return []


def match_alerts(summaries):
    """
    Match new episode topics against subscriber keywords.

    Args:
        summaries: list of summary dicts from the pipeline

    Returns:
        list of dicts: [{subscriber, matching_episodes: [{episode, matched_keywords}]}]
    """
    subscribers = load_subscriptions()
    active = [s for s in subscribers if s.get('active', True)]

    if not active:
        return []

    alerts = []
    for sub in active:
        keywords = [kw.lower().strip() for kw in sub.get('keywords', []) if kw.strip()]
        if not keywords:
            continue

        matching_episodes = []
        for summary in summaries:
            # Build searchable text from episode
            searchable = ' '.join([
                summary.get('summary', ''),
                ' '.join(summary.get('science_topics', [])),
                ' '.join(summary.get('claims_to_note', [])),
                ' '.join(summary.get('policy_relevance', [])),
                summary.get('episode_title', ''),
            ]).lower()

            matched_kw = [kw for kw in keywords if kw in searchable]
            if matched_kw:
                matching_episodes.append({
                    'podcast_name': summary.get('podcast_name', ''),
                    'episode_title': summary.get('episode_title', ''),
                    'summary': summary.get('summary', ''),
                    'science_topics': summary.get('science_topics', []),
                    'influence_tier': summary.get('influence_tier', 'emerging'),
                    'published': summary.get('published', ''),
                    'matched_keywords': matched_kw,
                })

        if matching_episodes:
            alerts.append({
                'email': sub['email'],
                'name': sub.get('name', ''),
                'matching_episodes': matching_episodes,
            })

    return alerts


def format_alert_html(alert):
    """
    Format an alert email as HTML for a single subscriber.

    Args:
        alert: dict with email, name, matching_episodes

    Returns:
        HTML string
    """
    today = datetime.now().strftime('%B %d, %Y')
    n_episodes = len(alert['matching_episodes'])
    name = alert.get('name', 'there')

    episodes_html = ''
    for ep in alert['matching_episodes']:
        tier = ep.get('influence_tier', 'emerging')
        tier_colors = {'high': '#c53030', 'medium': '#d69e2e', 'emerging': '#38a169'}
        tier_bg = tier_colors.get(tier, '#718096')

        keywords_html = ' '.join(
            f'<span style="background:#e9d8fd;color:#553c9a;padding:2px 8px;border-radius:12px;font-size:12px;">{kw}</span>'
            for kw in ep.get('matched_keywords', [])
        )

        topics_html = ' '.join(
            f'<span style="background:#f7fafc;color:#4a5568;padding:2px 8px;border-radius:12px;font-size:12px;">{t}</span>'
            for t in ep.get('science_topics', [])[:5]
        )

        episodes_html += f'''
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:12px;border-left:4px solid {tier_bg};">
            <span style="background:{tier_bg};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{tier.upper()} REACH</span>
            <h3 style="color:#2d3748;margin:8px 0 4px 0;">{ep["podcast_name"]}: {ep["episode_title"]}</h3>
            <p style="color:#4a5568;font-size:14px;margin:8px 0;">{ep.get("summary", "")[:300]}</p>
            <div style="margin:8px 0;">
                <span style="font-size:11px;color:#718096;font-weight:600;">MATCHED:</span> {keywords_html}
            </div>
            <div style="margin:4px 0;">
                <span style="font-size:11px;color:#718096;font-weight:600;">TOPICS:</span> {topics_html}
            </div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background:#f5f7fa; padding:20px;">
    <div style="max-width:600px; margin:0 auto; background:white; border-radius:12px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg, #553c9a 0%, #805ad5 100%); color:white; padding:24px; text-align:center;">
            <h1 style="margin:0; font-size:22px;">Topic Alert</h1>
            <p style="margin:8px 0 0 0; opacity:0.9; font-size:14px;">Science Podcast Monitor &mdash; {today}</p>
        </div>
        <div style="padding:24px;">
            <p style="color:#4a5568; font-size:15px; margin-bottom:20px;">
                Hi {name}, <strong>{n_episodes} new episode{"s" if n_episodes != 1 else ""}</strong>
                matched your topic subscriptions:
            </p>
            {episodes_html}
            <p style="margin-top:20px;font-size:13px;color:#a0aec0;">
                You're receiving this because of your keyword subscriptions.
                To update your preferences, reply to this email.
            </p>
        </div>
        <div style="background:#f8fafc; padding:16px; text-align:center; color:#718096; font-size:12px;">
            Science Podcast Monitor | National Academies of Sciences, Engineering, and Medicine
        </div>
    </div>
</body>
</html>'''

    return html


def send_alerts(alerts):
    """
    Send alert emails to all matching subscribers.

    Args:
        alerts: list from match_alerts()

    Returns:
        dict with sent count and errors
    """
    if not alerts:
        return {'sent': 0, 'errors': []}

    try:
        from email_sender import _get_gmail_service, _send_via_gmail, load_email_config, html_to_plain_text
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
    except ImportError as e:
        return {'sent': 0, 'errors': [f'Email imports failed: {e}']}

    config = load_email_config()
    sent = 0
    errors = []

    for alert in alerts:
        try:
            html = format_alert_html(alert)
            n_eps = len(alert['matching_episodes'])

            message = MIMEMultipart('alternative')
            message['Subject'] = f'[Topic Alert] {n_eps} episode{"s" if n_eps != 1 else ""} matched your interests'
            message['From'] = f"{config.get('sender_name', 'Science Podcast Monitor')} <{config['sender_email']}>"
            message['To'] = alert['email']

            message.attach(MIMEText(html_to_plain_text(html), 'plain'))
            message.attach(MIMEText(html, 'html'))

            result = _send_via_gmail(message)
            if result.get('success'):
                sent += 1
                print(f"  [ALERT] Sent alert to {alert['email']} ({n_eps} matches)")
            else:
                errors.append(f"{alert['email']}: {result.get('message', 'unknown error')}")
        except Exception as e:
            errors.append(f"{alert['email']}: {e}")

    return {'sent': sent, 'errors': errors}
