# transcriber.py
# Transcribe podcast audio using OpenAI API

import os
import json
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, TRANSCRIPTION_MODEL, TRANSCRIPT_DIR


def get_openai_client():
    """Get OpenAI client."""
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY or create openai_api_key.txt")
    return OpenAI(api_key=OPENAI_API_KEY)


def transcribe_file(audio_path):
    """
    Transcribe a single audio file using OpenAI API.

    Returns transcript text.
    """
    client = get_openai_client()

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL,
            file=audio_file,
            response_format="text"
        )

    return transcript


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
    import re
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', '_', s)
    return s[:max_len].strip('_').lower()
