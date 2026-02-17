# topic_tracker.py
# Track when science topics first appear on each channel (podcast, Bluesky)
# to detect cross-channel propagation patterns

import os
import json
from datetime import datetime, timedelta


TIMELINE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'topic_timeline.json')

# Synonym map for topic normalization
# Maps variant terms to canonical form
SYNONYMS = {
    'artificial intelligence': 'AI',
    'machine learning': 'AI',
    'deep learning': 'AI',
    'large language models': 'AI',
    'llm': 'AI',
    'llms': 'AI',
    'generative ai': 'AI',
    'gen ai': 'AI',
    'forever chemicals': 'PFAS',
    'pfos': 'PFAS',
    'per- and polyfluoroalkyl': 'PFAS',
    'climate change': 'climate change',
    'global warming': 'climate change',
    'climate crisis': 'climate change',
    'gene editing': 'CRISPR/gene editing',
    'crispr': 'CRISPR/gene editing',
    'crispr-cas9': 'CRISPR/gene editing',
    'genome editing': 'CRISPR/gene editing',
    'mental health': 'mental health',
    'depression': 'mental health',
    'anxiety disorders': 'mental health',
    'psychedelics': 'psychedelic therapy',
    'psilocybin': 'psychedelic therapy',
    'mdma therapy': 'psychedelic therapy',
    'psychedelic therapy': 'psychedelic therapy',
    'quantum computing': 'quantum computing',
    'quantum computer': 'quantum computing',
    'quantum computers': 'quantum computing',
    'obesity drugs': 'GLP-1/obesity drugs',
    'glp-1': 'GLP-1/obesity drugs',
    'ozempic': 'GLP-1/obesity drugs',
    'semaglutide': 'GLP-1/obesity drugs',
    'wegovy': 'GLP-1/obesity drugs',
    'tirzepatide': 'GLP-1/obesity drugs',
    'mounjaro': 'GLP-1/obesity drugs',
    'microplastics': 'microplastics',
    'nanoplastics': 'microplastics',
    'plastic pollution': 'microplastics',
    'bird flu': 'avian influenza',
    'avian flu': 'avian influenza',
    'h5n1': 'avian influenza',
    'avian influenza': 'avian influenza',
}


def normalize_topic(topic):
    """Normalize a topic name using synonym map and lowercasing."""
    lower = topic.lower().strip()
    return SYNONYMS.get(lower, topic.strip())


def load_timeline():
    """Load existing topic timeline from disk."""
    if os.path.exists(TIMELINE_FILE):
        try:
            with open(TIMELINE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_timeline(timeline):
    """Save topic timeline to disk."""
    with open(TIMELINE_FILE, 'w', encoding='utf-8') as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)


def record_podcast_topics(summaries):
    """
    Record topic appearances from podcast episode summaries.

    Args:
        summaries: list of summary dicts from the pipeline

    Returns:
        Updated timeline dict
    """
    timeline = load_timeline()

    for summary in summaries:
        podcast_name = summary.get('podcast_name', 'Unknown')
        published = summary.get('published', datetime.now().isoformat())
        episode_title = summary.get('episode_title', '')

        for topic in summary.get('science_topics', []):
            canonical = normalize_topic(topic)
            key = canonical.lower()

            if key not in timeline:
                timeline[key] = {
                    'canonical_name': canonical,
                    'channels': {},
                    'first_seen': published,
                    'total_mentions': 0,
                }

            entry = timeline[key]
            entry['total_mentions'] += 1

            channel_key = f"podcast:{podcast_name}"
            if channel_key not in entry['channels']:
                entry['channels'][channel_key] = {
                    'type': 'podcast',
                    'name': podcast_name,
                    'first_seen': published,
                    'mentions': [],
                }

            entry['channels'][channel_key]['mentions'].append({
                'date': published,
                'context': episode_title,
            })

            # Keep mentions list manageable (last 20 per channel)
            entry['channels'][channel_key]['mentions'] = \
                entry['channels'][channel_key]['mentions'][-20:]

            # Update global first_seen
            if published and published < entry.get('first_seen', published):
                entry['first_seen'] = published

    save_timeline(timeline)
    print(f"  [TRACKER] Updated timeline ({len(timeline)} topics tracked)")
    return timeline


def record_bluesky_topics(bluesky_data):
    """
    Record topic appearances from Bluesky Science Feed data.

    Args:
        bluesky_data: dict from bluesky_monitor.get_bluesky_digest()

    Returns:
        Updated timeline dict
    """
    timeline = load_timeline()
    now = datetime.now().isoformat()

    trending = bluesky_data.get('trending_topics', [])
    for item in trending:
        topic = item.get('topic', '')
        if not topic:
            continue

        canonical = normalize_topic(topic)
        key = canonical.lower()

        if key not in timeline:
            timeline[key] = {
                'canonical_name': canonical,
                'channels': {},
                'first_seen': now,
                'total_mentions': 0,
            }

        entry = timeline[key]
        entry['total_mentions'] += item.get('post_count', 1)

        channel_key = 'bluesky:science_feed'
        if channel_key not in entry['channels']:
            entry['channels'][channel_key] = {
                'type': 'bluesky',
                'name': 'Bluesky Science Feed',
                'first_seen': now,
                'mentions': [],
            }

        entry['channels'][channel_key]['mentions'].append({
            'date': now,
            'context': item.get('description', ''),
        })

        entry['channels'][channel_key]['mentions'] = \
            entry['channels'][channel_key]['mentions'][-20:]

    save_timeline(timeline)
    return timeline


def get_cross_channel_topics(days=14):
    """
    Get topics that have appeared on 2+ different channels recently.

    Args:
        days: Look back this many days

    Returns:
        list of dicts with topic info and channel timeline
    """
    timeline = load_timeline()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    cross_channel = []
    for key, data in timeline.items():
        # Filter to channels with recent activity
        recent_channels = {}
        for ch_key, ch_data in data.get('channels', {}).items():
            recent_mentions = [
                m for m in ch_data.get('mentions', [])
                if m.get('date', '') >= cutoff
            ]
            if recent_mentions:
                recent_channels[ch_key] = {
                    'type': ch_data['type'],
                    'name': ch_data['name'],
                    'first_seen': ch_data['first_seen'],
                    'recent_mentions': recent_mentions,
                }

        if len(recent_channels) >= 2:
            cross_channel.append({
                'topic': data['canonical_name'],
                'first_seen': data['first_seen'],
                'total_mentions': data['total_mentions'],
                'channel_count': len(recent_channels),
                'channels': recent_channels,
            })

    # Sort by channel count then total mentions
    cross_channel.sort(key=lambda x: (x['channel_count'], x['total_mentions']), reverse=True)
    return cross_channel
