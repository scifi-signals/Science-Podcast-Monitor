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
  "executive_summary": "5-8 sentence meta-summary covering the most important findings across all sources",
  "shared_talking_points": ["topics that appeared across multiple sources"],
  "emerging_trends": ["new topics gaining traction"],
  "nasem_opportunities": ["where NASEM could engage, respond, or promote its work"],
  "misinformation_watch": ["notable claims contradicting scientific consensus, if any"]
}}

PODCAST SUMMARIES:
{podcast_summaries}

BLUESKY TRENDS:
{bluesky_summary}"""


def generate_meta_summary(podcast_summaries, bluesky_digest):
    """
    Generate a meta-summary across all sources.

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


def build_digest(podcast_summaries, bluesky_digest, cross_channel_topics=None):
    """
    Build the complete digest data structure.

    Args:
        podcast_summaries: list of episode summary dicts
        bluesky_digest: dict from bluesky_monitor
        cross_channel_topics: list of cross-channel topic dicts from topic_tracker

    Returns dict ready for HTML formatting.
    """
    # Sort podcasts by influence tier
    sorted_podcasts = sort_by_influence(podcast_summaries)

    # Generate meta-summary
    meta = generate_meta_summary(podcast_summaries, bluesky_digest)

    digest = {
        "date": datetime.now().strftime("%B %d, %Y"),
        "timestamp": datetime.now().isoformat(),
        "meta_summary": meta,
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
