"""
Gemini AI integration for content analysis and comparison.
Uses Google AI Studio free tier (gemini-2.0-flash).
"""

import json
import re
import google.generativeai as genai

# ── Prompts ──────────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """
Analyze the following content thoroughly and return ONLY valid JSON (no markdown, no extra text).

Return this exact JSON structure:
{{
  "title": "A concise, descriptive title for this content",
  "executive_summary": "A clear 2-3 paragraph summary covering the main message, context, and significance",
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "action_items": ["actionable item 1", "actionable item 2"],
  "important_quotes": ["notable quote or key statement 1", "notable quote or key statement 2"],
  "topics": [
    {{"name": "Topic Name", "relevance": 85, "description": "What this topic covers in the content"}}
  ],
  "sentiment": "positive",
  "key_statistics": ["any numbers, percentages, data points mentioned"],
  "tags": ["tag1", "tag2", "tag3"],
  "difficulty_level": "beginner",
  "content_type": "educational",
  "word_count_estimate": 1500,
  "top_takeaway": "The single most important thing to remember from this content"
}}

Rules:
- "sentiment" must be one of: positive, negative, neutral, mixed
- "difficulty_level" must be one of: beginner, intermediate, advanced
- "content_type" must be one of: educational, news, opinion, tutorial, discussion, research, interview, review, other
- "topics" array: 3 to 8 items, each with relevance as integer 0-100
- "key_insights": 5 to 10 items
- "action_items": 3 to 7 items
- "important_quotes": 3 to 5 items
- "tags": 5 to 10 items

Content to analyze:
---
{content}
---
"""

COMPARISON_PROMPT = """
You are comparing multiple pieces of content on related topics.
Return ONLY valid JSON (no markdown, no extra text).

Return this exact JSON structure:
{{
  "overall_theme": "The overarching theme connecting all content",
  "common_themes": ["theme 1", "theme 2", "theme 3"],
  "key_agreements": ["point where sources agree 1", "point where sources agree 2"],
  "key_contradictions": ["contradiction or tension 1", "contradiction or tension 2"],
  "unique_insights_per_item": [
    {{"title": "Item title", "unique_insights": ["unique insight 1", "unique insight 2"]}}
  ],
  "consolidated_action_items": ["consolidated action 1", "consolidated action 2"],
  "trend_analysis": "A paragraph describing trends, patterns, and evolution of ideas across these sources",
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],
  "knowledge_gaps": ["topic or angle not covered that would be valuable"],
  "overall_sentiment": "mixed",
  "consensus_level": "high"
}}

Rules:
- "overall_sentiment" must be one of: positive, negative, neutral, mixed
- "consensus_level" must be one of: high, medium, low (how much sources agree)
- "unique_insights_per_item": one entry per input item

Content summaries to compare:
---
{content}
---
"""

SEARCH_PROMPT = """
Given the following knowledge base items, find the ones most relevant to this search query.
Return ONLY valid JSON with this structure:
{{
  "relevant_ids": ["id1", "id2"],
  "relevance_explanation": "Brief explanation of why these items match"
}}

Search query: {query}

Knowledge base items:
{items}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _init_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash")


def _parse_json(text: str) -> dict:
    """Extract and parse JSON from model response."""
    # Strip markdown code blocks if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from response:\n{text[:500]}")


def _truncate(text: str, max_chars: int = 60_000) -> str:
    """Truncate text to stay within Gemini's practical limit."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[... content truncated for length ...]\n\n" + text[-half:]


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_content(text: str, api_key: str) -> dict:
    """
    Run full analysis on a piece of text.
    Returns a structured dict with summary, insights, topics, etc.
    """
    model = _init_model(api_key)
    prompt = ANALYSIS_PROMPT.format(content=_truncate(text))
    response = model.generate_content(prompt)
    return _parse_json(response.text)


def compare_items(items: list[dict], api_key: str) -> dict:
    """
    Compare multiple analyzed items.
    `items` should be list of dicts with keys: id, title, executive_summary, key_insights, topics
    """
    model = _init_model(api_key)
    content_block = ""
    for i, item in enumerate(items, 1):
        content_block += f"\n--- Item {i}: {item.get('title', 'Untitled')} ---\n"
        content_block += f"Summary: {item.get('executive_summary', '')}\n"
        insights = item.get("key_insights", [])
        if insights:
            content_block += "Key Insights:\n" + "\n".join(f"- {ins}" for ins in insights) + "\n"
        topics = item.get("topics", [])
        if topics:
            content_block += "Topics: " + ", ".join(t["name"] for t in topics) + "\n"

    prompt = COMPARISON_PROMPT.format(content=content_block)
    response = model.generate_content(prompt)
    return _parse_json(response.text)


def semantic_search(query: str, items: list[dict], api_key: str) -> list[str]:
    """
    Return IDs of items most relevant to query.
    `items` should be list of dicts with keys: id, title, executive_summary, tags
    """
    if not items:
        return []
    model = _init_model(api_key)
    items_text = ""
    for item in items:
        items_text += f"ID: {item['id']} | Title: {item.get('title', '')} | "
        items_text += f"Summary: {item.get('executive_summary', '')[:300]} | "
        items_text += f"Tags: {', '.join(item.get('tags', []))}\n"

    prompt = SEARCH_PROMPT.format(query=query, items=items_text)
    response = model.generate_content(prompt)
    result = _parse_json(response.text)
    return result.get("relevant_ids", [])
