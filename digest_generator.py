# digest_generator.py
# Collate podcast summaries + Bluesky trends and generate meta-summary

import json
from datetime import datetime
from llm import ask_llm
from influence_scorer import sort_by_influence


META_SYSTEM_PROMPT = (
    "You are producing a daily intelligence briefing for NASEM leadership. "
    "Be concise, specific, and actionable. "
    "Respond ONLY with valid JSON. No markdown, no code fences."
)

META_USER_PROMPT = """Below are today's summaries from {n_podcasts} podcast episode(s) and \
Bluesky Science Feed data ({n_bluesky} posts analyzed). Generate a JSON object:

{{
  "executive_summary": "5-8 sentence meta-summary covering the most important findings across all sources. Reference multi-day patterns when the recent context shows recurring or evolving topics.",
  "shared_talking_points": ["topics that appeared across multiple sources"],
  "emerging_trends": ["new topics gaining traction — note if they also appeared in the past week"],
  "nasem_opportunities": ["where NASEM could engage, respond, or promote its work"],
  "misinformation_watch": ["notable claims contradicting scientific consensus, if any"]
}}

TODAY'S PODCAST SUMMARIES:
{podcast_summaries}

BLUESKY TRENDS:
{bluesky_summary}

RECENT CONTEXT (past 7 days):
{recent_context}

CROSS-CHANNEL PATTERNS (topics on 2+ channels in last 14 days):
{cross_channel_context}"""


TREND_SYSTEM_PROMPT = (
    "You are a science-policy trend analyst for NASEM leadership. "
    "Identify narrative threads across multiple podcast shows and Bluesky. "
    "Be specific — cite which shows discussed a topic. "
    "Respond ONLY with valid JSON. No markdown, no code fences."
)

TREND_USER_PROMPT = """Analyze these cross-channel topics and recent episode summaries to identify \
3-5 trend narratives for NASEM leadership.

For each trend, explain: what's converging across shows, what's emerging, or what's fading.

Return a JSON array:
[
  {{
    "topic": "Short topic label",
    "narrative": "2-3 sentence analysis of the trend — what's happening, why now, how shows are covering it differently or similarly",
    "shows": ["Show Name 1", "Show Name 2"],
    "nasem_relevance": "One sentence on why this matters for NASEM"
  }}
]

CROSS-CHANNEL TOPICS (appeared on 2+ channels, last 14 days):
{cross_channel_context}

RECENT EPISODE SUMMARIES (last 7 days):
{recent_context}"""


def _format_recent_context(recent_summaries):
    """Condense recent summaries into ~1 line each for LLM context."""
    if not recent_summaries:
        return "No recent episode data available."
    lines = []
    for s in recent_summaries:
        name = s.get('podcast_name', '?')
        date = s.get('published', '')[:10]
        topics = ', '.join(s.get('science_topics', [])[:4])
        lines.append(f"- {name} ({date}): {topics}")
    return '\n'.join(lines)


def _format_cross_channel_context(cross_channel_topics):
    """Format cross-channel topics for LLM context."""
    if not cross_channel_topics:
        return "No cross-channel patterns detected yet."
    lines = []
    for t in cross_channel_topics[:10]:
        name = t.get('topic', '?')
        n_ch = t.get('channel_count', 0)
        channels = t.get('channels', {})
        show_names = [ch.get('name', k) for k, ch in channels.items()]
        lines.append(f"- {name} ({n_ch} channels: {', '.join(show_names)})")
    return '\n'.join(lines)


def generate_meta_summary(podcast_summaries, bluesky_digest,
                          cross_channel_topics=None, recent_summaries=None):
    """
    Generate a meta-summary across all sources with multi-day context.

    Returns dict with executive summary, talking points, trends, opportunities.
    """
    if not podcast_summaries and not bluesky_digest.get("trending_topics"):
        return {
            "executive_summary": "No new content to summarize today.",
            "shared_talking_points": [],
            "emerging_trends": [],
            "nasem_opportunities": [],
            "misinformation_watch": [],
        }

    # Format podcast summaries for the prompt
    podcast_text = ""
    for s in podcast_summaries:
        tier = s.get("influence_tier", "emerging").upper()
        podcast_text += f"\n[{tier}] {s['podcast_name']} — {s['episode_title']}\n"
        podcast_text += f"Summary: {s.get('summary', 'N/A')}\n"
        topics = s.get("science_topics", [])
        if topics:
            podcast_text += f"Topics: {', '.join(topics)}\n"
        claims = s.get("claims_to_note", [])
        if claims:
            podcast_text += f"Claims: {'; '.join(claims[:3])}\n"

    # Format Bluesky summary
    bluesky_text = ""
    for topic in bluesky_digest.get("trending_topics", []):
        bluesky_text += f"- {topic.get('topic', '?')}: {topic.get('description', '')}\n"
    if not bluesky_text:
        bluesky_text = "No significant Bluesky trends detected."

    prompt = META_USER_PROMPT.format(
        n_podcasts=len(podcast_summaries),
        n_bluesky=bluesky_digest.get("post_count", 0),
        podcast_summaries=podcast_text or "None processed today.",
        bluesky_summary=bluesky_text,
        recent_context=_format_recent_context(recent_summaries),
        cross_channel_context=_format_cross_channel_context(cross_channel_topics),
    )

    print("  Generating meta-summary...")
    response = ask_llm(prompt, system_prompt=META_SYSTEM_PROMPT)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        meta = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        print("  [WARN] Failed to parse meta-summary JSON")
        meta = {
            "executive_summary": response[:500],
            "shared_talking_points": [],
            "emerging_trends": [],
            "nasem_opportunities": [],
            "misinformation_watch": [],
        }

    return meta


def generate_trend_synthesis(cross_channel_topics, recent_summaries):
    """
    Generate 3-5 trend narratives from cross-channel data and recent history.

    Returns list of trend dicts with topic, narrative, shows, nasem_relevance.
    """
    if not cross_channel_topics and not recent_summaries:
        return []

    prompt = TREND_USER_PROMPT.format(
        cross_channel_context=_format_cross_channel_context(cross_channel_topics),
        recent_context=_format_recent_context(recent_summaries),
    )

    print("  Generating trend synthesis...")
    response = ask_llm(prompt, system_prompt=TREND_SYSTEM_PROMPT)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        trends = json.loads(cleaned.strip())
        if not isinstance(trends, list):
            trends = []
    except json.JSONDecodeError:
        print("  [WARN] Failed to parse trend synthesis JSON")
        trends = []

    return trends


def build_digest(podcast_summaries, bluesky_digest, cross_channel_topics=None,
                 recent_summaries=None):
    """
    Build the complete digest data structure.

    Args:
        podcast_summaries: list of episode summary dicts
        bluesky_digest: dict from bluesky_monitor
        cross_channel_topics: list of cross-channel topic dicts from topic_tracker
        recent_summaries: list of episode summaries from past 7 days

    Returns dict ready for HTML formatting.
    """
    # Sort podcasts by influence tier
    sorted_podcasts = sort_by_influence(podcast_summaries)

    # Generate meta-summary with multi-day context
    meta = generate_meta_summary(
        podcast_summaries, bluesky_digest,
        cross_channel_topics=cross_channel_topics,
        recent_summaries=recent_summaries,
    )

    # Generate trend synthesis if we have cross-channel or recent data
    trend_synthesis = []
    if cross_channel_topics or recent_summaries:
        try:
            trend_synthesis = generate_trend_synthesis(
                cross_channel_topics or [], recent_summaries or []
            )
        except Exception as e:
            print(f"  [WARN] Trend synthesis failed: {e}")

    digest = {
        "date": datetime.now().strftime("%B %d, %Y"),
        "timestamp": datetime.now().isoformat(),
        "meta_summary": meta,
        "trend_synthesis": trend_synthesis,
        "podcast_episodes": sorted_podcasts,
        "bluesky": bluesky_digest,
        "cross_channel_topics": cross_channel_topics or [],
        "stats": {
            "episodes_processed": len(podcast_summaries),
            "bluesky_posts_analyzed": bluesky_digest.get("post_count", 0),
            "topics_extracted": sum(
                len(s.get("science_topics", []))
                for s in podcast_summaries
            ),
            "nasem_matches": sum(
                len(s.get("nasem_matches", []))
                for s in podcast_summaries
            ),
        },
    }

    return digest
