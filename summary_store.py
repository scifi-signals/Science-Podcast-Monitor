# summary_store.py
# Persist structured episode summaries as JSON for topic search and flow tracking

import os
import json
import re
from datetime import datetime


SUMMARY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'summaries')


def _safe_filename(s, max_len=50):
    """Convert a string to a safe filename fragment."""
    s = re.sub(r'[^\w\s-]', '', s.lower())
    s = re.sub(r'[\s]+', '_', s.strip())
    return s[:max_len]


def _get_summary_path(summary):
    """Build the file path for a summary JSON."""
    podcast_id = summary.get('podcast_id', 'unknown')
    published = summary.get('published', '')

    # Extract date from published ISO string
    try:
        dt = datetime.fromisoformat(published)
        date_str = dt.strftime('%Y%m%d')
    except (ValueError, TypeError):
        date_str = datetime.now().strftime('%Y%m%d')

    title = _safe_filename(summary.get('episode_title', 'untitled'))
    filename = f"{podcast_id}_{date_str}_{title}.json"
    return os.path.join(SUMMARY_DIR, filename)


def save_summary(summary):
    """
    Save a single episode summary to disk.

    Args:
        summary: dict from summarizer + NASEM matcher (contains podcast_id,
                 episode_title, summary, science_topics, claims_to_note,
                 policy_relevance, key_quotes, nasem_matches, etc.)
    """
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    stored = {
        'podcast_id': summary.get('podcast_id', ''),
        'podcast_name': summary.get('podcast_name', ''),
        'episode_title': summary.get('episode_title', ''),
        'host': summary.get('host', ''),
        'published': summary.get('published', ''),
        'duration_minutes': summary.get('duration_minutes', 0),
        'influence_tier': summary.get('influence_tier', 'emerging'),
        'category': summary.get('category', ''),
        'summary': summary.get('summary', ''),
        'science_topics': summary.get('science_topics', []),
        'claims_to_note': summary.get('claims_to_note', []),
        'policy_relevance': summary.get('policy_relevance', []),
        'key_quotes': summary.get('key_quotes', []),
        'nasem_matches': summary.get('nasem_matches', []),
        'word_count': summary.get('word_count', 0),
        'saved_at': datetime.now().isoformat(),
    }

    filepath = _get_summary_path(summary)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(stored, f, indent=2, ensure_ascii=False)

    print(f"  [STORE] Saved summary: {os.path.basename(filepath)}")
    return filepath


def load_all_summaries():
    """
    Load all stored summaries from disk.

    Returns:
        list of summary dicts, sorted by published date (newest first)
    """
    if not os.path.exists(SUMMARY_DIR):
        return []

    summaries = []
    for filename in os.listdir(SUMMARY_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(SUMMARY_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['_filename'] = filename
                summaries.append(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  [WARN] Failed to load {filename}: {e}")

    # Sort by published date (newest first)
    def sort_key(s):
        try:
            return datetime.fromisoformat(s.get('published', ''))
        except (ValueError, TypeError):
            return datetime.min

    summaries.sort(key=sort_key, reverse=True)
    return summaries


def load_recent_summaries(days=90):
    """Load summaries from the last N days."""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=days)

    all_summaries = load_all_summaries()
    recent = []
    for s in all_summaries:
        try:
            pub_date = datetime.fromisoformat(s.get('published', ''))
            if pub_date >= cutoff:
                recent.append(s)
        except (ValueError, TypeError):
            # Include if we can't parse the date (better to include than exclude)
            recent.append(s)

    return recent
