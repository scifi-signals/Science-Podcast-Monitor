# Science Podcast Monitor

Daily podcast intelligence for NASEM. Monitors 20 science podcasts, transcribes episodes, summarizes with LLM, matches to NASEM publications, generates digest with email delivery.

## How to Run

```bash
python main.py                 # Full pipeline (RSS → transcribe → summarize → digest)
python main.py --max 3         # Limit to 3 episodes
python main.py --dry-run       # Check feeds without processing
python main.py --podcast-only  # Skip Bluesky monitoring
python main.py --bluesky-only  # Skip podcasts
python main.py --email         # Generate and email
python main.py --send-last     # Email most recent digest
```

## Deployment

- **GitHub:** `scifi-signals/Science-Podcast-Monitor`
- **Server:** DigitalOcean (`science-intel` / 159.203.126.156)
- **Schedule:** Daily 6am ET via GitHub Actions (`daily-monitor.yml`) + DigitalOcean cron (`run_monitor.sh`)
- **Secrets:** OPENAI_API_KEY + ANTHROPIC_API_KEY on GitHub; key files on server

## Pipeline

1. `rss_monitor.py` — Check 20 feeds for new episodes (3-day lookback)
2. `audio_downloader.py` — Download + compress audio (ffmpeg, 64k, 15-min chunks)
3. `transcriber.py` — OpenAI `gpt-4o-mini-transcribe`
4. `summarizer.py` — Claude Haiku 4.5 (topics, claims, policy relevance, key quotes)
5. `nasem_matcher.py` — Match to 1,300+ publications (keyword + LLM fallback)
6. `bluesky_monitor.py` — Bluesky Science Feed (48-hour window)
7. `topic_tracker.py` — Cross-channel topic tracking
8. `digest_generator.py` + `html_formatter.py` — HTML digest (Jinja2)
9. `email_sender.py` — Gmail REST API
10. `update_site.py` — GitHub Pages manifest

## Key Files

- `main.py` — Orchestrator
- `config.py` — API keys, models, paths
- `podcasts.json` — 20 active feeds (4 categories)
- `nasem_catalog.json` — NASEM publication database
- `history.json` — Processed episodes (avoids reprocessing)
- `data/summaries/` — Stored summaries for search

## 20 Podcasts (4 Categories)

- **Science Policy (6):** Laws of Notion, Science Policy IRL, Science for Policy, Science of Politics, Unbiased Science, Science Will Win
- **High-Reach Influencers (5):** Huberman Lab, Peter Attia Drive, Found My Fitness, Radiolab, StarTalk
- **Long-form Interview (3):** Lex Fridman, Making Sense, Ezra Klein Show
- **Science News (6):** Science Friday, TechTank, Short Wave, Nature Podcast, Science Magazine, Skeptics' Guide

## Technical Gotchas

- **ffmpeg directly, NOT pydub** — pydub causes OOM on 1GB droplet
- **Browser User-Agent header** needed for Acast CDN (TechTank)
- **15-min time-based chunking** (not file-size) due to OpenAI token limits
- **Python 3.12** has audioop built-in; 3.13+ needs `audioop-lts`
- **2GB swap** added to server for large audio processing
- **Gmail REST API** because DigitalOcean blocks SMTP ports

## API Keys

- `OPENAI_API_KEY` / `openai_api_key.txt` — Transcription
- `ANTHROPIC_API_KEY` / `anthropic_api_key.txt` — Summarization
- `credentials.json` / `token.json` — Gmail OAuth
