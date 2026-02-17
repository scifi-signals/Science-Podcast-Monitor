# influence_scorer.py
# Weight and sort content by influence tier

TIER_ORDER = {"high": 0, "medium": 1, "emerging": 2}
TIER_EMOJI = {"high": "\U0001f534", "medium": "\U0001f7e1", "emerging": "\U0001f7e2"}
TIER_LABEL = {"high": "HIGH", "medium": "MEDIUM", "emerging": "EMERGING"}

# Bluesky follower thresholds
BLUESKY_HIGH = 50000
BLUESKY_MEDIUM = 10000
BLUESKY_EMERGING = 1000


def get_podcast_tier(episode):
    """Get influence tier for a podcast episode (from config)."""
    return episode.get("influence_tier", "emerging").lower()


def get_bluesky_tier(followers_count):
    """Calculate influence tier from Bluesky follower count."""
    if followers_count >= BLUESKY_HIGH:
        return "high"
    elif followers_count >= BLUESKY_MEDIUM:
        return "medium"
    elif followers_count >= BLUESKY_EMERGING:
        return "emerging"
    return "emerging"


def sort_by_influence(items, tier_key="influence_tier", date_key="published"):
    """
    Sort items by influence tier (high first), then by date (newest first).

    Returns sorted list.
    """
    def sort_key(item):
        tier = item.get(tier_key, "emerging").lower()
        tier_rank = TIER_ORDER.get(tier, 2)
        # Use date string for secondary sort (ISO format sorts correctly)
        date = item.get(date_key, "")
        return (tier_rank, "" if not date else date)

    return sorted(items, key=sort_key)


def tier_badge_html(tier):
    """Generate HTML badge for a tier."""
    tier = tier.lower()
    colors = {
        "high": ("#c53030", "#fff5f5"),
        "medium": ("#d69e2e", "#fffff0"),
        "emerging": ("#38a169", "#f0fff4"),
    }
    bg, _ = colors.get(tier, ("#718096", "#f7fafc"))
    label = TIER_LABEL.get(tier, "UNKNOWN")
    emoji = TIER_EMOJI.get(tier, "")
    return f'<span style="background:{bg};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold;">{emoji} {label}</span>'
