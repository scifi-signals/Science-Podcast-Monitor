# audio_downloader.py
# Download and prepare podcast audio for transcription

import os
import tempfile
import requests
from config import MAX_AUDIO_FILE_SIZE_MB, COMPRESS_BITRATE


def download_audio(audio_url, episode_id="episode"):
    """
    Download audio file from URL.

    Returns path to downloaded file, or None on failure.
    """
    print(f"  Downloading audio...")

    try:
        response = requests.get(audio_url, stream=True, timeout=300)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] Download failed: {e}")
        return None

    # Determine file extension
    content_type = response.headers.get('content-type', '')
    if 'mp3' in content_type or audio_url.endswith('.mp3'):
        ext = '.mp3'
    elif 'm4a' in content_type or audio_url.endswith('.m4a'):
        ext = '.m4a'
    elif 'wav' in content_type or audio_url.endswith('.wav'):
        ext = '.wav'
    else:
        ext = '.mp3'

    # Save to temp file
    tmp_dir = tempfile.mkdtemp(prefix='spm_')
    filepath = os.path.join(tmp_dir, f"{episode_id}{ext}")

    total_bytes = 0
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            total_bytes += len(chunk)

    size_mb = total_bytes / (1024 * 1024)
    print(f"  Downloaded: {size_mb:.1f} MB")

    return filepath


def compress_audio(filepath, force=False):
    """
    Compress audio to 64kbps mono MP3.
    Always compresses to ensure consistent quality and small chunk sizes.

    Returns path to compressed file (may be same as input if already small enough).
    """
    size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if not force and size_mb <= MAX_AUDIO_FILE_SIZE_MB and filepath.endswith('.mp3'):
        return filepath

    print(f"  File is {size_mb:.1f} MB (limit: {MAX_AUDIO_FILE_SIZE_MB} MB), compressing...")

    try:
        from pydub import AudioSegment
    except ImportError:
        print("  [ERROR] pydub not installed. Run: pip install pydub")
        print("  [ERROR] Also need ffmpeg installed on system.")
        return filepath

    try:
        audio = AudioSegment.from_file(filepath)
        # Convert to mono, lower bitrate
        audio = audio.set_channels(1)

        compressed_path = filepath.rsplit('.', 1)[0] + '_compressed.mp3'
        audio.export(compressed_path, format='mp3', bitrate=COMPRESS_BITRATE)

        new_size_mb = os.path.getsize(compressed_path) / (1024 * 1024)
        print(f"  Compressed: {size_mb:.1f} MB -> {new_size_mb:.1f} MB")

        # Clean up original
        os.remove(filepath)

        return compressed_path

    except Exception as e:
        print(f"  [ERROR] Compression failed: {e}")
        return filepath


def chunk_audio(filepath, chunk_minutes=15):
    """
    Split audio file into time-based chunks for transcription API.
    Uses 15-minute chunks to stay well within token limits.

    Returns list of chunk file paths.
    """
    try:
        from pydub import AudioSegment
    except ImportError:
        print("  [ERROR] pydub not installed for chunking")
        return [filepath]

    try:
        audio = AudioSegment.from_file(filepath)
        duration_ms = len(audio)
        duration_min = duration_ms / 60000

        # No chunking needed for short audio
        if duration_min <= chunk_minutes:
            return [filepath]

        chunk_duration_ms = chunk_minutes * 60 * 1000
        num_chunks = int(duration_ms / chunk_duration_ms) + (1 if duration_ms % chunk_duration_ms else 0)

        print(f"  Chunking {duration_min:.0f} min audio into {num_chunks} x {chunk_minutes} min pieces...")

        chunks = []
        for i in range(num_chunks):
            start = i * chunk_duration_ms
            end = min((i + 1) * chunk_duration_ms, duration_ms)
            chunk = audio[start:end]

            chunk_path = filepath.rsplit('.', 1)[0] + f'_chunk{i}.mp3'
            chunk.export(chunk_path, format='mp3', bitrate=COMPRESS_BITRATE)
            chunks.append(chunk_path)

        print(f"  Split into {len(chunks)} chunks")
        return chunks

    except Exception as e:
        print(f"  [ERROR] Chunking failed: {e}")
        return [filepath]


def prepare_audio(audio_url, episode_id="episode"):
    """
    Full pipeline: download, compress if needed, chunk if needed.

    Returns list of audio file paths ready for transcription.
    """
    filepath = download_audio(audio_url, episode_id)
    if not filepath:
        return []

    # Always compress large files; compress everything to ensure consistent format
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    filepath = compress_audio(filepath, force=(size_mb > MAX_AUDIO_FILE_SIZE_MB))
    chunks = chunk_audio(filepath)

    return chunks


def cleanup_audio(file_paths):
    """Remove temporary audio files after transcription."""
    for path in file_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    # Try to remove temp directories
    dirs = set(os.path.dirname(p) for p in file_paths)
    for d in dirs:
        try:
            if os.path.isdir(d) and d.startswith(tempfile.gettempdir()):
                os.rmdir(d)
        except OSError:
            pass
