# config.py
# Configuration for Science Podcast Monitor

import os

# ======================
# LLM PROVIDER SETTINGS
# ======================
LLM_PROVIDER = "anthropic"  # "anthropic", "openai", or "grok"

def _load_api_key(env_var, filename):
    """Load API key from environment or local file."""
    key = os.environ.get(env_var, "")
    if key:
        return key
    key_path = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    return ""

ANTHROPIC_API_KEY = _load_api_key("ANTHROPIC_API_KEY", "anthropic_api_key.txt")
OPENAI_API_KEY = _load_api_key("OPENAI_API_KEY", "openai_api_key.txt")
GROK_API_KEY = _load_api_key("GROK_API_KEY", "grok_api_key.txt")

LLM_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "grok": "grok-4",
}

LLM_MAX_TOKENS = 4096

# ======================
# TRANSCRIPTION SETTINGS
# ======================
TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
MAX_AUDIO_FILE_SIZE_MB = 25
COMPRESS_BITRATE = "64k"

# ======================
# NASEM MATCHING
# ======================
USE_LLM_FALLBACK_FOR_MATCHING = False

# ======================
# PODCAST SETTINGS
# ======================
PODCAST_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'podcasts.json')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')
TRANSCRIPT_DIR = os.path.join(os.path.dirname(__file__), 'data', 'transcripts')

# How many days back to check for new episodes
EPISODE_LOOKBACK_DAYS = 3
