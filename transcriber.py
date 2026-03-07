# transcriber.py
# Transcribe podcast audio using Groq's Whisper API (OpenAI-compatible)

import os
import json
import re
import time
from datetime import datetime
from openai import OpenAI, RateLimitError
from config import GROQ_API_KEY, TRANSCRIPTION_MODEL, TRANSCRIPT_DIR


def get_groq_client():
    """Get Groq client (OpenAI-compatible)."""
    if not GROQ_API_KEY:
        raise ValueError("Groq API key not configured. Set GROQ_API_KEY environment variable")
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def _parse_retry_seconds(error_message):
    """Parse 'try again in XmYs' from Groq rate limit error."""
    match = re.search(r'try again in (\d+)m([\d.]+)s', str(error_message))
    if match:
        return int(match.group(1)) * 60 + float(match.group(2))
    match = re.search(r'try again in ([\d.]+)s', str(error_message))
    if match:
        return float(match.group(1))
    match = re.search(r'try again in (\d+)m', str(error_message))
    if match:
        return int(match.group(1)) * 60
    return 120  # Default 2 min wait if can't parse


def transcribe_file(audio_path, max_retries=3):
    """
    Transcribe a single audio file using Groq Whisper API.
    Retries on rate limit errors with the wait time from the error message.

    Returns transcript text.
    """
    client = get_groq_client()

    for attempt in range(max_retries):
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=TRANSCRIPTION_MODEL,
                    file=audio_file,
                    response_format="text",
                    language="en",
                )
            return transcript
        except RateLimitError as e:
            wait_seconds = _parse_retry_seconds(str(e))
            # Add 10s buffer
            wait_seconds = min(wait_seconds + 10, 300)
            if attempt < max_retries - 1:
                print(f"    Rate limited. Waiting {wait_seconds:.0f}s...")
                time.sleep(wait_seconds)
            else:
                raise


def transcribe_chunks(chunk_paths):
    """
    Transcribe multiple audio chunks and concatenate.

    Returns full transcript text.
    """
    if len(chunk_paths) == 1:
        return transcribe_file(chunk_paths[0])

    print(f"  Transcribing {len(chunk_paths)} chunks...")
    parts = []
    for i, path in enumerate(chunk_paths):
        print(f"    Chunk {i+1}/{len(chunk_paths)}...")
        text = transcribe_file(path)
        parts.append(text)
        # Pace requests to stay under Groq's 20 RPM free-tier limit
        if i < len(chunk_paths) - 1:
            time.sleep(4)

    return "\n\n".join(parts)


def transcribe_episode(audio_paths, episode):
    """
    Transcribe an episode and save the transcript.

    Args:
        audio_paths: List of audio file paths (may be chunked)
        episode: Episode metadata dict

    Returns:
        dict with transcript text and metadata
    """
    podcast_name = episode.get('podcast_name', 'Unknown')
    title = episode.get('title', 'Untitled')

    print(f"  Transcribing: {title}...")

    transcript_text = transcribe_chunks(audio_paths)
    word_count = len(transcript_text.split())

    print(f"  Transcribed: {word_count:,} words")

    # Build transcript record
    transcript = {
        'podcast_id': episode.get('podcast_id', ''),
        'podcast_name': podcast_name,
        'episode_title': title,
        'host': episode.get('host', ''),
        'published': episode.get('published', ''),
        'duration_minutes': episode.get('duration_minutes'),
        'influence_tier': episode.get('influence_tier', 'emerging'),
        'category': episode.get('category', ''),
        'episode_url': episode.get('episode_url', ''),
        'transcript': transcript_text,
        'word_count': word_count,
        'transcribed_at': datetime.now().isoformat(),
        'model': TRANSCRIPTION_MODEL,
    }

    # Save transcript to disk
    save_transcript(transcript, episode)

    return transcript


def save_transcript(transcript, episode):
    """Save transcript to data/transcripts/ directory."""
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

    podcast_id = episode.get('podcast_id', 'unknown')
    date_str = datetime.now().strftime('%Y%m%d')
    filename = f"{podcast_id}_{date_str}_{_safe_filename(episode.get('title', 'untitled'))}.json"
    filepath = os.path.join(TRANSCRIPT_DIR, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)

    print(f"  Saved transcript: {filename}")


def _safe_filename(s, max_len=50):
    """Convert string to safe filename."""
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', '_', s)
    return s[:max_len].strip('_').lower()
