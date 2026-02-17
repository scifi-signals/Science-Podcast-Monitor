# generate_topic_index.py
# Build topic_index.json and timeline_data.json from stored summaries
# for client-side search on GitHub Pages

import os
import json
from datetime import datetime
from summary_store import load_recent_summaries


def build_topic_index(days=90):
    """
    Build a search index from recent episode summaries.

    Returns list of episode entries with searchable fields.
    """
    summaries = load_recent_summaries(days=days)

    index = []
    for s in summaries:
        # Flatten NASEM matches for search
        nasem_pubs = []
        for match in s.get('nasem_matches', []):
            for pub in match.get('publications', []):
                nasem_pubs.append({
                    'title': pub.get('title', ''),
                    'url': pub.get('url', ''),
                })

        entry = {
            'podcast_id': s.get('podcast_id', ''),
            'podcast_name': s.get('podcast_name', ''),
            'episode_title': s.get('episode_title', ''),
            'host': s.get('host', ''),
            'published': s.get('published', ''),
            'influence_tier': s.get('influence_tier', 'emerging'),
            'category': s.get('category', ''),
            'summary': s.get('summary', ''),
            'science_topics': s.get('science_topics', []),
            'claims_to_note': s.get('claims_to_note', []),
            'policy_relevance': s.get('policy_relevance', []),
            'nasem_publications': nasem_pubs,
        }
        index.append(entry)

    return index


def save_topic_index(index):
    """Write topic_index.json to repo root for GitHub Pages."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, 'topic_index.json')

    data = {
        'updated': datetime.now().isoformat(),
        'episode_count': len(index),
        'episodes': index,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Built topic index with {len(index)} episodes")
    return filepath


def build_timeline_data(index):
    """
    Build timeline_data.json for the timeline visualization page.

    Extracts all topics with their first appearance dates and channels.
    """
    topic_map = {}  # normalized_topic -> {first_seen, channels: {channel: [dates]}}

    for ep in index:
        published = ep.get('published', '')
        podcast_name = ep.get('podcast_name', '')

        for topic in ep.get('science_topics', []):
            norm = topic.lower().strip()
            if norm not in topic_map:
                topic_map[norm] = {
                    'topic': topic,  # keep original casing from first occurrence
                    'first_seen': published,
                    'channels': {},
                    'mention_count': 0,
                }

            entry = topic_map[norm]
            entry['mention_count'] += 1

            if podcast_name not in entry['channels']:
                entry['channels'][podcast_name] = []
            entry['channels'][podcast_name].append({
                'date': published,
                'episode': ep.get('episode_title', ''),
            })

            # Update first_seen if this is earlier
            if published and (not entry['first_seen'] or published < entry['first_seen']):
                entry['first_seen'] = published

    # Filter to multi-channel topics (appeared on 2+ different podcasts)
    cross_channel = []
    for norm, data in topic_map.items():
        if len(data['channels']) >= 2:
            cross_channel.append({
                'topic': data['topic'],
                'first_seen': data['first_seen'],
                'mention_count': data['mention_count'],
                'channel_count': len(data['channels']),
                'channels': data['channels'],
            })

    # Sort by mention count descending
    cross_channel.sort(key=lambda x: x['mention_count'], reverse=True)

    return cross_channel


def save_timeline_data(timeline):
    """Write timeline_data.json to repo root for GitHub Pages."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, 'timeline_data.json')

    data = {
        'updated': datetime.now().isoformat(),
        'cross_channel_topic_count': len(timeline),
        'topics': timeline,
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Built timeline data with {len(timeline)} cross-channel topics")
    return filepath


if __name__ == '__main__':
    print("Building topic index...")
    index = build_topic_index(days=90)
    save_topic_index(index)

    print("\nBuilding timeline data...")
    timeline = build_timeline_data(index)
    save_timeline_data(timeline)

    print("\nDone!")
