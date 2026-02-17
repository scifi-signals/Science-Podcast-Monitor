# summarizer.py
# LLM summarization of podcast transcripts

import json
from llm import ask_llm


PODCAST_SYSTEM_PROMPT = """You are a science policy analyst at the National Academies of Sciences, \
Engineering, and Medicine (NASEM). Your job is to analyze podcast transcripts and \
extract information relevant to science policy, public health, technology policy, \
and scientific research.

Respond ONLY with valid JSON. No markdown, no code fences, no extra text."""


PODCAST_USER_PROMPT = """Analyze the following podcast transcript and return a JSON object with these fields:

{{
  "summary": "3-5 sentence summary of the main topics and key arguments",
  "science_topics": ["list of specific scientific topics discussed, e.g. 'CRISPR gene editing', 'methane emissions from agriculture' — be specific, not broad"],
  "claims_to_note": ["list of specific factual claims about science, health, or policy that could be verified against NASEM reports — flag anything contradicting scientific consensus"],
  "policy_relevance": ["list of any mentions of legislation, regulation, federal agencies, funding decisions, or policy debates"],
  "key_quotes": ["2-3 notable direct quotes that capture the episode's most significant points"]
}}

Podcast: {podcast_name}
Episode: {episode_title}
Date: {episode_date}
Host: {host_name}

TRANSCRIPT:
{transcript_text}"""


def summarize_episode(transcript):
    """
    Summarize a podcast episode transcript using LLM.

    Args:
        transcript: dict with transcript text and episode metadata

    Returns:
        dict with summary, topics, claims, policy relevance, key quotes
    """
    podcast_name = transcript.get('podcast_name', 'Unknown')
    episode_title = transcript.get('episode_title', 'Untitled')

    print(f"  Summarizing: {episode_title}...")

    # Truncate very long transcripts to stay within token limits
    text = transcript.get('transcript', '')
    max_chars = 100000  # ~25K tokens, well within Haiku's 200K context
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[TRANSCRIPT TRUNCATED]"

    prompt = PODCAST_USER_PROMPT.format(
        podcast_name=podcast_name,
        episode_title=episode_title,
        episode_date=transcript.get('published', 'Unknown'),
        host_name=transcript.get('host', 'Unknown'),
        transcript_text=text,
    )

    response = ask_llm(prompt, system_prompt=PODCAST_SYSTEM_PROMPT)

    # Parse JSON response
    try:
        # Strip any markdown code fences
        cleaned = response.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1]
        if cleaned.endswith('```'):
            cleaned = cleaned.rsplit('```', 1)[0]
        cleaned = cleaned.strip()

        summary = json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"  [WARN] Failed to parse LLM response as JSON, using raw text")
        summary = {
            "summary": response[:500],
            "science_topics": [],
            "claims_to_note": [],
            "policy_relevance": [],
            "key_quotes": [],
            "parse_error": True,
        }

    # Attach episode metadata
    summary['podcast_id'] = transcript.get('podcast_id', '')
    summary['podcast_name'] = podcast_name
    summary['episode_title'] = episode_title
    summary['host'] = transcript.get('host', '')
    summary['published'] = transcript.get('published', '')
    summary['duration_minutes'] = transcript.get('duration_minutes')
    summary['influence_tier'] = transcript.get('influence_tier', 'emerging')
    summary['category'] = transcript.get('category', '')
    summary['word_count'] = transcript.get('word_count', 0)

    topic_count = len(summary.get('science_topics', []))
    print(f"  Extracted {topic_count} science topics")

    return summary


if __name__ == '__main__':
    # Test with a sample transcript
    test_transcript = {
        'podcast_name': 'Test Podcast',
        'episode_title': 'Test Episode',
        'published': '2026-02-16',
        'host': 'Test Host',
        'transcript': 'This is a test transcript about CRISPR gene editing and its applications in treating sickle cell disease. The FDA recently approved a new gene therapy...',
        'influence_tier': 'medium',
    }
    result = summarize_episode(test_transcript)
    print(json.dumps(result, indent=2))
