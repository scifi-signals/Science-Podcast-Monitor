# audio_downloader.py
# Download and prepare podcast audio for transcription
# Uses ffmpeg directly (not pydub) to avoid loading entire files into RAM

import os
import shutil
import subprocess
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


def _get_duration_seconds(filepath):
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
            capture_output=True, text=True, timeout=30
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def compress_audio(filepath, force=False):
    """
    Compress audio to 64kbps mono MP3 using ffmpeg directly.
    Streams data instead of loading into RAM.

    Returns path to compressed file.
    """
    size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if not force and size_mb <= MAX_AUDIO_FILE_SIZE_MB and filepath.endswith('.mp3'):
        return filepath

    print(f"  File is {size_mb:.1f} MB (limit: {MAX_AUDIO_FILE_SIZE_MB} MB), compressing...")

    if not shutil.which('ffmpeg'):
        print("  [ERROR] ffmpeg not found on system. Install ffmpeg.")
        return filepath

    try:
        compressed_path = filepath.rsplit('.', 1)[0] + '_compressed.mp3'
        result = subprocess.run(
            ['ffmpeg', '-i', filepath, '-ac', '1', '-ab', COMPRESS_BITRATE,
             '-y', compressed_path],
            capture_output=True, text=True, timeout=600
        )

        if result.returncode != 0:
            print(f"  [ERROR] ffmpeg failed: {result.stderr[-200:]}")
            return filepath

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
    Split audio file into time-based chunks using ffmpeg directly.
    Uses segment muxer to avoid loading entire file into RAM.

    Returns list of chunk file paths.
    """
    if not shutil.which('ffmpeg'):
        print("  [ERROR] ffmpeg not found for chunking")
        return [filepath]

    try:
        duration = _get_duration_seconds(filepath)
        if duration is None:
            print("  [WARN] Could not determine duration, skipping chunking")
            return [filepath]

        duration_min = duration / 60

        # No chunking needed for short audio
        if duration_min <= chunk_minutes:
            return [filepath]

        chunk_seconds = chunk_minutes * 60
        num_chunks = int(duration / chunk_seconds) + (1 if duration % chunk_seconds else 0)
        print(f"  Chunking {duration_min:.0f} min audio into {num_chunks} x {chunk_minutes} min pieces...")

        base = filepath.rsplit('.', 1)[0]
        pattern = f"{base}_chunk%03d.mp3"

        result = subprocess.run(
            ['ffmpeg', '-i', filepath, '-f', 'segment', '-segment_time', str(chunk_seconds),
             '-ac', '1', '-ab', COMPRESS_BITRATE, '-y', pattern],
            capture_output=True, text=True, timeout=600
        )

        if result.returncode != 0:
            print(f"  [ERROR] Chunking failed: {result.stderr[-200:]}")
            return [filepath]

        # Find the generated chunk files
        chunk_dir = os.path.dirname(filepath)
        chunk_base = os.path.basename(base) + '_chunk'
        chunks = sorted([
            os.path.join(chunk_dir, f) for f in os.listdir(chunk_dir)
            if f.startswith(chunk_base) and f.endswith('.mp3')
        ])

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

    # Always compress large files
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
