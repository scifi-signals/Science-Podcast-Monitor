# bluesky_monitor.py
# Monitor the Bluesky Science Feed for trending science discussions

import requests
import json
import os
from datetime import datetime, timedelta
from config import HISTORY_FILE

# Bluesky public API (no auth needed for reading public data)
PUBLIC_API = "https://public.api.bsky.app/xrpc"

# The Bluesky Science Feed — curated, verified scientists
SCIENCE_FEED_URI = "at://did:plc:jfhpnnst6flqway4eaeqzj2a/app.bsky.feed.generator/for-science"

# Minimum engagement thresholds
MIN_LIKES = 5
MIN_REPOSTS = 2


def get_feed_posts(feed_uri=None, limit=100):
    """
    Fetch recent posts from the Bluesky Science Feed.

    Returns list of post dicts with text, author, engagement metrics.
    """
    if feed_uri is None:
        feed_uri = SCIENCE_FEED_URI

    print(f"  Fetching Bluesky Science Feed...")

    all_posts = []
    cursor = None
    pages = 0
    max_pages = 4  # 4 pages x 30 = up to 120 posts

    while pages < max_pages:
        params = {"feed": feed_uri, "limit": 30}
        if cursor:
            params["cursor"] = cursor

        try:
            response = requests.get(
                f"{PUBLIC_API}/app.bsky.feed.getFeed",
                params=params,
                timeout=15,
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"  [ERROR] Bluesky API error: {e}")
            break

        feed_items = data.get("feed", [])
        if not feed_items:
            break

        for item in feed_items:
            post = item.get("post", {})
            record = post.get("record", {})
            author = post.get("author", {})

            # Extract engagement
            like_count = post.get("likeCount", 0)
            repost_count = post.get("repostCount", 0)
            reply_count = post.get("replyCount", 0)

            # Parse post creation time
            created_at = record.get("createdAt", "")

            # Build post URL from URI
            uri = post.get("uri", "")
            post_url = _uri_to_url(uri, author.get("handle", ""))

            all_posts.append({
                "text": record.get("text", ""),
                "author_handle": author.get("handle", ""),
                "author_name": author.get("displayName", ""),
                "author_avatar": author.get("avatar", ""),
                "followers_count": author.get("followersCount", 0),
                "like_count": like_count,
                "repost_count": repost_count,
                "reply_count": reply_count,
                "created_at": created_at,
                "uri": uri,
                "url": post_url,
                "has_link": bool(record.get("embed")),
            })

        cursor = data.get("cursor")
        if not cursor:
            break
        pages += 1

    print(f"  Fetched {len(all_posts)} posts from Science Feed")
    return all_posts


def get_profile(handle):
    """Get a Bluesky user's profile including follower count."""
    try:
        response = requests.get(
            f"{PUBLIC_API}/app.bsky.actor.getProfile",
            params={"actor": handle},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def filter_posts(posts, min_likes=None, min_reposts=None, hours_back=24):
    """
    Filter posts by engagement and recency.

    Returns filtered list sorted by engagement (likes + reposts).
    """
    if min_likes is None:
        min_likes = MIN_LIKES
    if min_reposts is None:
        min_reposts = MIN_REPOSTS

    cutoff = datetime.utcnow() - timedelta(hours=hours_back)
    filtered = []

    for post in posts:
        # Check recency
        try:
            post_time = datetime.fromisoformat(post["created_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            if post_time < cutoff:
                continue
        except (ValueError, KeyError):
            pass  # Keep posts with unparseable dates

        # Check engagement (either likes OR reposts meet threshold)
        if post["like_count"] >= min_likes or post["repost_count"] >= min_reposts:
            filtered.append(post)

    # Sort by total engagement
    filtered.sort(key=lambda p: p["like_count"] + p["repost_count"], reverse=True)

    return filtered


def summarize_bluesky_posts(posts):
    """
    Summarize a batch of Bluesky posts using LLM.

    Returns dict with trending topics, notable posts, NASEM-relevant mentions.
    """
    if not posts:
        return {
            "trending_topics": [],
            "notable_posts": [],
            "nasem_relevant": [],
            "post_count": 0,
        }

    from llm import ask_llm

    # Format posts for the LLM
    formatted = []
    for i, post in enumerate(posts[:50]):  # Limit to 50 posts
        formatted.append(
            f"[{i+1}] @{post['author_handle']} ({post['followers_count']:,} followers, "
            f"{post['like_count']} likes, {post['repost_count']} reposts):\n"
            f"{post['text'][:500]}"
        )

    posts_text = "\n\n".join(formatted)

    system_prompt = (
        "You are a science policy analyst at NASEM. Analyze Bluesky Science Feed posts "
        "and identify trending topics and notable discussions. "
        "Respond ONLY with valid JSON. No markdown, no code fences."
    )

    user_prompt = f"""Analyze these {len(formatted)} posts from the Bluesky Science Feed (collected {datetime.now().strftime('%B %d, %Y')}). Return a JSON object:

{{
  "trending_topics": [
    {{"topic": "specific topic name", "post_count": approximate_count, "description": "1 sentence"}}
  ],
  "notable_posts": [
    {{"author": "@handle", "followers": count, "summary": "1 sentence summary", "post_index": N}}
  ],
  "nasem_relevant": [
    {{"topic": "topic name", "connection": "how it relates to NASEM work"}}
  ],
  "misinformation_flags": [
    {{"claim": "the claim", "concern": "why it's concerning"}}
  ]
}}

Limit to top 5 trending topics, top 5 notable posts, top 3 NASEM-relevant items.

POSTS:
{posts_text}"""

    print(f"  Summarizing {len(formatted)} Bluesky posts...")

    response = ask_llm(user_prompt, system_prompt=system_prompt)

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]

        summary = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        print(f"  [WARN] Failed to parse Bluesky summary as JSON")
        summary = {
            "trending_topics": [],
            "notable_posts": [],
            "nasem_relevant": [],
            "parse_error": True,
        }

    summary["post_count"] = len(posts)
    summary["filtered_count"] = len(formatted)

    topic_count = len(summary.get("trending_topics", []))
    print(f"  Identified {topic_count} trending topics from Bluesky")

    return summary


def get_bluesky_digest(hours_back=48):
    """
    Full Bluesky pipeline: fetch feed → filter → summarize.

    Returns dict with trending topics, notable posts, raw posts.
    """
    print(f"\n[BLUESKY] Monitoring Science Feed...")

    # Fetch posts
    posts = get_feed_posts()

    if not posts:
        print("  No posts retrieved from Science Feed")
        return {"post_count": 0, "trending_topics": [], "notable_posts": []}

    # Filter by engagement and recency
    filtered = filter_posts(posts, hours_back=hours_back)
    print(f"  {len(filtered)} posts with significant engagement (last {hours_back}h)")

    if not filtered:
        print("  No high-engagement posts found")
        return {"post_count": len(posts), "trending_topics": [], "notable_posts": []}

    # Summarize via LLM
    summary = summarize_bluesky_posts(filtered)

    # Attach top raw posts for the digest
    summary["top_posts"] = filtered[:10]

    return summary


def _uri_to_url(uri, handle):
    """Convert AT Protocol URI to Bluesky web URL."""
    # at://did:plc:xxx/app.bsky.feed.post/yyy → https://bsky.app/profile/handle/post/yyy
    try:
        parts = uri.split("/")
        post_id = parts[-1]
        return f"https://bsky.app/profile/{handle}/post/{post_id}"
    except (IndexError, AttributeError):
        return ""


if __name__ == "__main__":
    result = get_bluesky_digest(hours_back=48)
    print(f"\nResults:")
    print(f"  Total posts: {result.get('post_count', 0)}")
    print(f"  Trending topics: {len(result.get('trending_topics', []))}")
    for topic in result.get("trending_topics", []):
        print(f"    - {topic.get('topic', '?')}: {topic.get('description', '')}")
    print(f"  Notable posts: {len(result.get('notable_posts', []))}")
