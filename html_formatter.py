# html_formatter.py
# Format the podcast monitor digest as a professional HTML email/page

import os
from datetime import datetime
from influence_scorer import tier_badge_html, TIER_EMOJI, TIER_LABEL


def format_digest_html(digest):
    """
    Format the complete digest as an HTML page/email.

    Args:
        digest: dict from digest_generator.build_digest()

    Returns:
        HTML string
    """
    date = digest.get("date", datetime.now().strftime("%B %d, %Y"))
    meta = digest.get("meta_summary", {})
    episodes = digest.get("podcast_episodes", [])
    bluesky = digest.get("bluesky", {})
    stats = digest.get("stats", {})

    # Build sections
    meta_html = _format_meta_summary(meta)
    episodes_html = _format_episodes(episodes)
    bluesky_html = _format_bluesky(bluesky)
    methodology_html = _format_methodology(stats)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Science Podcast Monitor - {date}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #2d3748;
            line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #553c9a 0%, #6b46c1 50%, #805ad5 100%);
            color: white;
            padding: 32px 24px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .subtitle {{ opacity: 0.9; font-size: 16px; }}
        .header .date {{ opacity: 0.7; font-size: 14px; margin-top: 4px; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 24px 16px; }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #553c9a;
            font-size: 20px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e9d8fd;
        }}
        .card h3 {{ color: #2d3748; font-size: 16px; margin-bottom: 8px; }}
        .episode {{
            border-left: 4px solid #805ad5;
            padding: 16px;
            margin-bottom: 16px;
            background: #faf5ff;
            border-radius: 0 8px 8px 0;
        }}
        .episode-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }}
        .episode-title {{ font-weight: 700; color: #2d3748; font-size: 16px; }}
        .episode-meta {{ color: #718096; font-size: 13px; }}
        .topic-tag {{
            display: inline-block;
            background: #e9d8fd;
            color: #553c9a;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            margin: 2px 4px 2px 0;
        }}
        .claim {{
            background: #fff5f5;
            border-left: 3px solid #fc8181;
            padding: 8px 12px;
            margin: 8px 0;
            font-size: 14px;
            border-radius: 0 6px 6px 0;
        }}
        .nasem-match {{
            background: #f0fff4;
            border-left: 3px solid #68d391;
            padding: 8px 12px;
            margin: 8px 0;
            font-size: 14px;
            border-radius: 0 6px 6px 0;
        }}
        .nasem-match a {{ color: #276749; text-decoration: none; font-weight: 600; }}
        .nasem-match a:hover {{ text-decoration: underline; }}
        .quote {{
            font-style: italic;
            color: #4a5568;
            padding: 8px 16px;
            border-left: 3px solid #805ad5;
            margin: 8px 0;
            font-size: 14px;
        }}
        .bluesky-post {{
            background: #ebf8ff;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
        }}
        .bluesky-author {{ font-weight: 600; color: #2b6cb0; font-size: 14px; }}
        .bluesky-stats {{ color: #718096; font-size: 12px; }}
        .bluesky-text {{ font-size: 14px; margin-top: 4px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-bottom: 16px;
        }}
        .stat-box {{
            background: #f7fafc;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }}
        .stat-number {{ font-size: 28px; font-weight: 700; color: #553c9a; }}
        .stat-label {{ font-size: 12px; color: #718096; }}
        .opportunity {{
            background: #fffff0;
            border-left: 3px solid #ecc94b;
            padding: 8px 12px;
            margin: 4px 0;
            font-size: 14px;
            border-radius: 0 6px 6px 0;
        }}
        .footer {{
            text-align: center;
            color: #a0aec0;
            font-size: 12px;
            padding: 24px;
            margin-top: 12px;
        }}
        .section-divider {{ height: 1px; background: #e2e8f0; margin: 16px 0; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 4px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Science Podcast Monitor</h1>
        <div class="subtitle">Daily Intelligence Digest for NASEM</div>
        <div class="date">{date}</div>
    </div>
    <div class="container">
        {_format_stats(stats)}
        {meta_html}
        {episodes_html}
        {bluesky_html}
        {methodology_html}
    </div>
    <div class="footer">
        Science Podcast Monitor | National Academies of Sciences, Engineering, and Medicine<br>
        Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} | Internal use only
    </div>
</body>
</html>"""

    return html


def _format_stats(stats):
    """Format the stats bar at the top."""
    return f"""
    <div class="card">
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-number">{stats.get('episodes_processed', 0)}</div>
                <div class="stat-label">Episodes Processed</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats.get('topics_extracted', 0)}</div>
                <div class="stat-label">Topics Extracted</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats.get('nasem_matches', 0)}</div>
                <div class="stat-label">NASEM Matches</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{stats.get('bluesky_posts_analyzed', 0)}</div>
                <div class="stat-label">Bluesky Posts</div>
            </div>
        </div>
    </div>"""


def _format_meta_summary(meta):
    """Format the executive meta-summary section."""
    if not meta.get("executive_summary"):
        return ""

    html = '<div class="card">\n'
    html += '<h2>Executive Summary</h2>\n'
    html += f'<p style="font-size:15px;line-height:1.7;">{meta["executive_summary"]}</p>\n'

    # Shared talking points
    points = meta.get("shared_talking_points", [])
    if points:
        html += '<div class="section-divider"></div>\n'
        html += '<h3>Shared Talking Points</h3>\n<ul>\n'
        for p in points:
            html += f'<li>{p}</li>\n'
        html += '</ul>\n'

    # Emerging trends
    trends = meta.get("emerging_trends", [])
    if trends:
        html += '<div class="section-divider"></div>\n'
        html += '<h3>Emerging Trends</h3>\n<ul>\n'
        for t in trends:
            html += f'<li>{t}</li>\n'
        html += '</ul>\n'

    # NASEM opportunities
    opps = meta.get("nasem_opportunities", [])
    if opps:
        html += '<div class="section-divider"></div>\n'
        html += '<h3>NASEM Opportunities</h3>\n'
        for o in opps:
            html += f'<div class="opportunity">{o}</div>\n'

    # Misinformation watch
    misinfo = meta.get("misinformation_watch", [])
    if misinfo:
        html += '<div class="section-divider"></div>\n'
        html += '<h3>Misinformation Watch</h3>\n'
        for m in misinfo:
            html += f'<div class="claim">{m}</div>\n'

    html += '</div>\n'
    return html


def _format_episodes(episodes):
    """Format podcast episode summaries."""
    if not episodes:
        return ""

    html = '<div class="card">\n'
    html += '<h2>Podcast Episodes</h2>\n'

    # Tier legend
    html += '<div style="margin-bottom:16px;padding:10px 14px;background:#f7fafc;border-radius:8px;font-size:12px;color:#718096;">\n'
    html += '  <strong>Influence Tiers:</strong> '
    html += '  <span style="background:#c53030;color:white;padding:1px 6px;border-radius:3px;font-size:11px;">HIGH REACH</span> '
    html += '  Top podcasts (est. 500K+ downloads/ep) &nbsp;&middot;&nbsp; '
    html += '  <span style="background:#d69e2e;color:white;padding:1px 6px;border-radius:3px;font-size:11px;">MEDIUM REACH</span> '
    html += '  Established niche shows &nbsp;&middot;&nbsp; '
    html += '  <span style="background:#38a169;color:white;padding:1px 6px;border-radius:3px;font-size:11px;">EMERGING</span> '
    html += '  Smaller/policy-focused shows'
    html += '</div>\n'

    for ep in episodes:
        tier = ep.get("influence_tier", "emerging")
        badge = _tier_reach_badge(tier)
        duration = f" &middot; {ep['duration_minutes']:.0f} min" if ep.get("duration_minutes") else ""
        published = ""
        if ep.get("published"):
            try:
                dt = datetime.fromisoformat(ep["published"])
                published = f" &middot; {dt.strftime('%b %d')}"
            except ValueError:
                pass

        html += '<div class="episode">\n'
        html += '<div class="episode-header">\n'
        html += f'  {badge}\n'
        html += f'  <span class="episode-title">{ep.get("podcast_name", "")}: {ep.get("episode_title", "")}</span>\n'
        html += '</div>\n'
        html += f'<div class="episode-meta">{ep.get("host", "")}{published}{duration}</div>\n'

        # Summary
        if ep.get("summary"):
            html += f'<p style="margin:10px 0;font-size:14px;">{ep["summary"]}</p>\n'

        # Science topics
        topics = ep.get("science_topics", [])
        if topics:
            html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#553c9a;text-transform:uppercase;letter-spacing:0.5px;">Topics Discussed</div>\n'
            html += '<div style="margin:4px 0 8px 0;">\n'
            for t in topics:
                html += f'  <span class="topic-tag">{t}</span>\n'
            html += '</div>\n'

        # NASEM matches
        matches = ep.get("nasem_matches", [])
        has_pubs = any(pub for match in matches for pub in match.get("publications", []))
        if has_pubs:
            html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#276749;text-transform:uppercase;letter-spacing:0.5px;">Related NASEM Publications</div>\n'
            for match in matches:
                pubs = match.get("publications", [])
                for pub in pubs[:2]:
                    title = pub.get("title", "")
                    url = pub.get("url", "")
                    if url:
                        html += f'<div class="nasem-match"><a href="{url}" target="_blank">{title}</a></div>\n'
                    else:
                        html += f'<div class="nasem-match">{title}</div>\n'

        # Claims to note
        claims = ep.get("claims_to_note", [])
        if claims:
            html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#c53030;text-transform:uppercase;letter-spacing:0.5px;">Claims to Verify</div>\n'
            html += '<p style="font-size:11px;color:#a0aec0;margin-bottom:4px;">Factual claims from the episode that may warrant review against NASEM reports</p>\n'
            for c in claims[:3]:
                html += f'<div class="claim">{c}</div>\n'

        # Key quotes
        quotes = ep.get("key_quotes", [])
        if quotes:
            html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#553c9a;text-transform:uppercase;letter-spacing:0.5px;">Key Quotes</div>\n'
            for q in quotes[:2]:
                html += f'<div class="quote">"{q}"</div>\n'

        html += '</div>\n'

    html += '</div>\n'
    return html


def _tier_reach_badge(tier):
    """Generate a descriptive HTML badge for a tier."""
    tier = tier.lower()
    config = {
        "high": ("#c53030", "HIGH REACH"),
        "medium": ("#d69e2e", "MEDIUM REACH"),
        "emerging": ("#38a169", "EMERGING"),
    }
    bg, label = config.get(tier, ("#718096", "UNKNOWN"))
    return f'<span style="background:{bg};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{label}</span>'


def _format_bluesky(bluesky):
    """Format Bluesky Science Feed section."""
    if not bluesky or bluesky.get("post_count", 0) == 0:
        return ""

    html = '<div class="card">\n'
    html += f'<h2>Bluesky Science Feed</h2>\n'
    html += f'<p class="episode-meta">{bluesky.get("post_count", 0)} posts analyzed from the curated <a href="https://bsky.app/profile/emily.bsky.team/feed/for-science" style="color:#2b6cb0;">For Science</a> feed</p>\n'

    # Trending topics
    topics = bluesky.get("trending_topics", [])
    if topics:
        html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#2b6cb0;text-transform:uppercase;letter-spacing:0.5px;">Trending Topics</div>\n'
        html += '<p style="font-size:11px;color:#a0aec0;margin-bottom:6px;">Most-discussed subjects among scientists on Bluesky in the last 48 hours</p>\n'
        for t in topics:
            topic_name = t.get("topic", "?")
            desc = t.get("description", "")
            count = t.get("post_count", "")
            count_str = f' ({count} posts)' if count else ""
            html += f'<div style="margin:6px 0;">'
            html += f'<span class="topic-tag">{topic_name}{count_str}</span> '
            html += f'<span style="font-size:13px;color:#4a5568;">{desc}</span>'
            html += '</div>\n'

    # Notable posts
    top_posts = bluesky.get("top_posts", [])
    if top_posts:
        html += '<div class="section-divider"></div>\n'
        html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#2b6cb0;text-transform:uppercase;letter-spacing:0.5px;">Notable Posts</div>\n'
        html += '<p style="font-size:11px;color:#a0aec0;margin-bottom:6px;">Highest-engagement posts from scientists and science communicators, ranked by likes and reposts</p>\n'
        for post in top_posts[:5]:
            html += '<div class="bluesky-post">\n'
            html += f'  <div class="bluesky-author">@{post.get("author_handle", "?")}'
            followers = post.get("followers_count", 0)
            if followers:
                html += f' ({followers:,} followers)'
            html += '</div>\n'
            html += f'  <div class="bluesky-stats">'
            html += f'{post.get("like_count", 0)} likes &middot; '
            html += f'{post.get("repost_count", 0)} reposts &middot; '
            html += f'{post.get("reply_count", 0)} replies'
            html += '</div>\n'
            text = post.get("text", "")[:300]
            html += f'  <div class="bluesky-text">{text}</div>\n'
            url = post.get("url", "")
            if url:
                html += f'  <div style="margin-top:4px;"><a href="{url}" target="_blank" style="color:#2b6cb0;font-size:12px;">View post</a></div>\n'
            html += '</div>\n'

    # NASEM relevant
    nasem_items = bluesky.get("nasem_relevant", [])
    if nasem_items:
        html += '<div class="section-divider"></div>\n'
        html += '<div style="margin:12px 0 4px 0;font-size:12px;font-weight:600;color:#276749;text-transform:uppercase;letter-spacing:0.5px;">NASEM-Relevant Mentions</div>\n'
        html += '<p style="font-size:11px;color:#a0aec0;margin-bottom:6px;">Bluesky discussions that connect to NASEM research areas or publications</p>\n'
        for item in nasem_items:
            html += f'<div class="nasem-match">'
            html += f'<strong>{item.get("topic", "?")}</strong>: {item.get("connection", "")}'
            html += '</div>\n'

    html += '</div>\n'
    return html


def _format_methodology(stats):
    """Format methodology/about section."""
    return f"""
    <div class="card" style="background:#f8fafc;">
        <h2 style="color:#718096;font-size:16px;">About This Digest</h2>
        <p style="font-size:13px;color:#718096;">
            This digest is automatically generated by the Science Podcast Monitor.
            It transcribes recent podcast episodes using OpenAI, summarizes them using Claude,
            and matches discussed topics to NASEM publications. Bluesky data comes from the
            curated Science Feed. All summaries are AI-generated &mdash; review source material
            for verification.
        </p>
    </div>"""


def save_digest(html_content, filename=None):
    """Save HTML digest to file."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        filename = f"digest_{timestamp}.html"

    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"  Saved digest: {filename}")
    return filepath
