# rss_monitor.py
# Check podcast RSS feeds for new episodes

import json
import os
from datetime import datetime, timedelta
import feedparser
from config import PODCAST_CONFIG_FILE, HISTORY_FILE, EPISODE_LOOKBACK_DAYS


def load_podcasts():
    """Load podcast configurations."""
    with open(PODCAST_CONFIG_FILE, 'r') as f:
        return [p for p in json.load(f) if p.get('active', True)]


def load_history():
    """Load processing history to avoid reprocessing episodes."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {"processed_episodes": [], "last_run": None}


def save_history(history):
    """Save processing history."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2, default=str)


def get_episode_guid(entry):
    """Get a unique identifier for an episode."""
    if hasattr(entry, 'id') and entry.id:
        return entry.id
    if hasattr(entry, 'link') and entry.link:
        return entry.link
    return entry.get('title', '') + entry.get('published', '')


def get_audio_url(entry):
    """Extract audio URL from RSS entry enclosures."""
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('audio/') or enc.get('href', '').endswith(('.mp3', '.m4a', '.wav')):
                return enc.get('href', '')
        # Fallback: return first enclosure
        return entry.enclosures[0].get('href', '')

    # Some feeds use media:content
    if hasattr(entry, 'media_content') and entry.media_content:
        for media in entry.media_content:
            if media.get('type', '').startswith('audio/'):
                return media.get('url', '')

    return None


def parse_duration(entry):
    """Try to extract episode duration in minutes."""
    # itunes:duration can be HH:MM:SS, MM:SS, or just seconds
    duration_str = entry.get('itunes_duration', '')
    if not duration_str:
        return None

    try:
        parts = str(duration_str).split(':')
        if len(parts) == 3:
            return int(parts[0]) * 60 + int(parts[1]) + int(parts[2]) / 60
        elif len(parts) == 2:
            return int(parts[0]) + int(parts[1]) / 60
        else:
            return int(duration_str) / 60
    except (ValueError, TypeError):
        return None


def check_feed(podcast, history, lookback_days=None):
    """
    Check a single podcast's RSS feed for new episodes.

    Returns list of new episode dicts.
    """
    if lookback_days is None:
        lookback_days = EPISODE_LOOKBACK_DAYS

    if not podcast.get('rss_url'):
        print(f"  [SKIP] {podcast['name']}: No RSS URL configured")
        return []

    print(f"  Checking {podcast['name']}...")

    try:
        feed = feedparser.parse(podcast['rss_url'])
    except Exception as e:
        print(f"  [ERROR] {podcast['name']}: Failed to parse feed: {e}")
        return []

    if feed.bozo and not feed.entries:
        print(f"  [ERROR] {podcast['name']}: Malformed feed")
        return []

    processed_guids = set(history.get('processed_episodes', []))
    cutoff = datetime.now() - timedelta(days=lookback_days)
    new_episodes = []

    for entry in feed.entries:
        guid = get_episode_guid(entry)

        # Skip already processed
        if guid in processed_guids:
            continue

        # Parse publish date
        published = None
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Skip old episodes
        if published and published < cutoff:
            continue

        audio_url = get_audio_url(entry)
        if not audio_url:
            continue

        episode = {
            'guid': guid,
            'podcast_id': podcast['id'],
            'podcast_name': podcast['name'],
            'host': podcast.get('host', ''),
            'title': entry.get('title', 'Untitled'),
            'description': entry.get('summary', entry.get('description', '')),
            'published': published.isoformat() if published else None,
            'audio_url': audio_url,
            'duration_minutes': parse_duration(entry),
            'influence_tier': podcast.get('influence_tier', 'emerging'),
            'category': podcast.get('category', ''),
        }
        new_episodes.append(episode)

    if new_episodes:
        print(f"  [OK] {podcast['name']}: {len(new_episodes)} new episode(s)")
    else:
        print(f"  [--] {podcast['name']}: No new episodes")

    return new_episodes


def check_all_feeds(lookback_days=None):
    """
    Check all active podcast feeds for new episodes.

    Returns list of new episode dicts.
    """
    podcasts = load_podcasts()
    history = load_history()

    print(f"\n[RSS] Checking {len(podcasts)} podcast feeds...")
    all_new = []

    for podcast in podcasts:
        episodes = check_feed(podcast, history, lookback_days)
        all_new.extend(episodes)

    print(f"\n[RSS] Found {len(all_new)} new episode(s) total")
    return all_new


def mark_processed(guids):
    """Mark episode GUIDs as processed in history."""
    history = load_history()
    processed = set(history.get('processed_episodes', []))
    processed.update(guids)
    history['processed_episodes'] = list(processed)
    history['last_run'] = datetime.now().isoformat()
    save_history(history)


if __name__ == '__main__':
    episodes = check_all_feeds(lookback_days=7)
    for ep in episodes:
        dur = f" ({ep['duration_minutes']:.0f} min)" if ep['duration_minutes'] else ""
        print(f"  - [{ep['podcast_name']}] {ep['title']}{dur}")
        print(f"    Audio: {ep['audio_url'][:80]}...")
