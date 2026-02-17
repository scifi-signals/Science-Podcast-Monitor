# main.py
# Science Podcast Monitor - Main Orchestrator

import sys
import os
import json
from datetime import datetime

from rss_monitor import check_all_feeds, mark_processed
from audio_downloader import prepare_audio, cleanup_audio
from transcriber import transcribe_episode
from summarizer import summarize_episode
from bluesky_monitor import get_bluesky_digest
from digest_generator import build_digest
from html_formatter import format_digest_html, save_digest


def process_episode(episode):
    """
    Process a single episode through the full pipeline:
    download -> transcribe -> summarize

    Returns summary dict, or None on failure.
    """
    title = episode.get('title', 'Untitled')
    podcast = episode.get('podcast_name', 'Unknown')
    print(f"\n{'='*60}")
    print(f"Processing: [{podcast}] {title}")
    print(f"{'='*60}")

    # Step 1: Download and prepare audio
    print("\n[1/3] AUDIO DOWNLOAD")
    audio_paths = prepare_audio(
        episode['audio_url'],
        episode_id=episode.get('podcast_id', 'ep')
    )
    if not audio_paths:
        print(f"  [ERROR] Failed to download audio, skipping episode")
        return None

    try:
        # Step 2: Transcribe
        print("\n[2/3] TRANSCRIPTION")
        transcript = transcribe_episode(audio_paths, episode)

        # Step 3: Summarize
        print("\n[3/3] SUMMARIZATION")
        summary = summarize_episode(transcript)

        return summary

    finally:
        # Always clean up audio files
        cleanup_audio(audio_paths)


def match_summaries_to_nasem(summaries):
    """Match extracted topics from summaries to NASEM publications."""
    try:
        from nasem_matcher import find_publications_for_topic, find_current_projects_for_topic
    except ImportError:
        print("[WARN] NASEM matcher not available, skipping publication matching")
        return summaries

    print(f"\n[NASEM] Matching topics to publications...")

    for summary in summaries:
        topics = summary.get('science_topics', [])
        matches = []

        for topic in topics[:5]:  # Limit to top 5 topics per episode
            pubs = find_publications_for_topic(topic, use_llm_fallback=False)
            projects = find_current_projects_for_topic(topic)

            if pubs or projects:
                matches.append({
                    'topic': topic,
                    'publications': pubs[:3],
                    'projects': projects[:2],
                })

        summary['nasem_matches'] = matches
        if matches:
            print(f"  [{summary['podcast_name']}] {len(matches)} topic(s) matched")

    return summaries


def run_pipeline(lookback_days=None, max_episodes=None, dry_run=False,
                 send_email=False, podcast_only=False, bluesky_only=False):
    """
    Run the full podcast monitoring pipeline.

    Args:
        lookback_days: How many days back to check for episodes
        max_episodes: Max episodes to process (for testing/cost control)
        dry_run: If True, only check RSS feeds without downloading/transcribing
        send_email: If True, send digest via email after generating
        podcast_only: Skip Bluesky monitoring
        bluesky_only: Skip podcast processing
    """
    print("=" * 60)
    print("  SCIENCE PODCAST MONITOR")
    print(f"  {datetime.now().strftime('%B %d, %Y %H:%M')}")
    print("=" * 60)

    summaries = []
    processed_guids = []
    bluesky_data = {"post_count": 0, "trending_topics": [], "notable_posts": []}

    # ===== PODCAST PIPELINE =====
    if not bluesky_only:
        episodes = check_all_feeds(lookback_days=lookback_days)

        if dry_run:
            print(f"\n[DRY RUN] Would process {len(episodes)} episode(s):")
            for ep in episodes:
                dur = f" ({ep['duration_minutes']:.0f} min)" if ep.get('duration_minutes') else ""
                print(f"  - [{ep['podcast_name']}] {ep['title']}{dur}")
            return

        if episodes:
            if max_episodes and len(episodes) > max_episodes:
                print(f"\nLimiting to {max_episodes} episode(s) (of {len(episodes)} found)")
                episodes = episodes[:max_episodes]

            for episode in episodes:
                try:
                    summary = process_episode(episode)
                    if summary:
                        summaries.append(summary)
                        processed_guids.append(episode['guid'])
                except Exception as e:
                    print(f"\n[ERROR] Failed to process episode: {e}")
                    continue

            # Match to NASEM publications
            if summaries:
                summaries = match_summaries_to_nasem(summaries)

            # Mark episodes as processed
            if processed_guids:
                mark_processed(processed_guids)
                print(f"\nMarked {len(processed_guids)} episode(s) as processed")
        else:
            print("\nNo new podcast episodes to process.")

    # ===== BLUESKY PIPELINE =====
    if not podcast_only:
        try:
            bluesky_data = get_bluesky_digest(hours_back=48)
        except Exception as e:
            print(f"\n[ERROR] Bluesky monitoring failed: {e}")

    # ===== DIGEST GENERATION =====
    if summaries or bluesky_data.get("post_count", 0) > 0:
        print(f"\n[DIGEST] Building digest...")

        digest = build_digest(summaries, bluesky_data)
        html = format_digest_html(digest)
        filepath = save_digest(html)

        # Send email if requested
        if send_email:
            print(f"\n[EMAIL] Sending digest...")
            try:
                from email_sender import send_digest_email, check_email_config
                status = check_email_config()
                if status['configured']:
                    result = send_digest_email(filepath)
                    if result['success']:
                        print(f"  [OK] {result['message']}")
                    else:
                        print(f"  [ERROR] {result['message']}")
                else:
                    print(f"  [SKIP] Email not configured: {status['message']}")
            except Exception as e:
                print(f"  [ERROR] Email failed: {e}")

        # Print summary
        print(f"\n{'='*60}")
        print(f"  COMPLETE")
        print(f"  Episodes: {len(summaries)}")
        print(f"  Bluesky posts: {bluesky_data.get('post_count', 0)}")
        print(f"  Digest: {os.path.basename(filepath)}")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  No new content to report.")
        print(f"{'='*60}")

    return summaries


def print_usage():
    print("""
Science Podcast Monitor

Usage:
  python main.py                  Run full pipeline (podcasts + Bluesky + digest)
  python main.py --email          Run pipeline and send digest via email
  python main.py --dry-run        Check feeds only, don't download/transcribe
  python main.py --max N          Process at most N episodes
  python main.py --lookback N     Check last N days for new episodes (default: 3)
  python main.py --rss-only       Just check RSS feeds and show new episodes
  python main.py --podcast-only   Skip Bluesky monitoring
  python main.py --bluesky-only   Skip podcast processing
  python main.py --test-email     Send a test email to verify configuration
  python main.py --setup          Show setup instructions
""")


if __name__ == '__main__':
    args = sys.argv[1:]

    if '--help' in args or '-h' in args:
        print_usage()
        sys.exit(0)

    if '--setup' in args:
        print("""
Setup Instructions:
  1. Install dependencies: pip install -r requirements.txt
  2. Install ffmpeg (for audio compression): https://ffmpeg.org/download.html
  3. Add API keys:
     - OpenAI: create openai_api_key.txt (needed for transcription)
     - Anthropic: create anthropic_api_key.txt (needed for summarization)
  4. Edit podcasts.json to configure which podcasts to monitor
  5. Set up email: python gmail_auth.py (see email_sender.py --setup)
  6. Run: python main.py --dry-run   (to test RSS feeds)
  7. Run: python main.py --max 1     (to test with one episode)
""")
        sys.exit(0)

    if '--test-email' in args:
        from email_sender import check_email_config, send_test_email
        print("Checking email configuration...")
        status = check_email_config()
        if not status['configured']:
            print(f"\n[!] {status['message']}")
        else:
            print(f"[OK] {status['message']}")
            print("\nSending test email...")
            result = send_test_email()
            if result['success']:
                print(f"[OK] {result['message']}")
            else:
                print(f"[!] {result['message']}")
        sys.exit(0)

    lookback_days = None
    max_episodes = None
    dry_run = '--dry-run' in args
    rss_only = '--rss-only' in args
    send_email = '--email' in args
    podcast_only = '--podcast-only' in args
    bluesky_only = '--bluesky-only' in args

    if '--lookback' in args:
        idx = args.index('--lookback')
        lookback_days = int(args[idx + 1])

    if '--max' in args:
        idx = args.index('--max')
        max_episodes = int(args[idx + 1])

    if rss_only:
        episodes = check_all_feeds(lookback_days=lookback_days or 7)
        for ep in episodes:
            dur = f" ({ep['duration_minutes']:.0f} min)" if ep.get('duration_minutes') else ""
            title = ep['title'].encode('ascii', 'replace').decode('ascii')
            print(f"  - [{ep['podcast_name']}] {title}{dur}")
            print(f"    Published: {ep.get('published', 'Unknown')}")
            print(f"    Audio: {ep['audio_url'][:80]}...")
    else:
        run_pipeline(
            lookback_days=lookback_days,
            max_episodes=max_episodes,
            dry_run=dry_run,
            send_email=send_email,
            podcast_only=podcast_only,
            bluesky_only=bluesky_only,
        )
