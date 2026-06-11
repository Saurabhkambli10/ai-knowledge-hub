"""
YouTube transcript extraction utilities.
Uses youtube-transcript-api (free, no API key required).
Compatible with both old (<0.7) and new (>=0.7) versions of the library.
"""

import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str | None:
    """
    Extract YouTube video ID from various URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    """
    url = url.strip()

    # youtu.be short link
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)

    # Standard watch URL
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            params = parse_qs(parsed.query)
            vid_id = params.get("v", [None])[0]
            if vid_id:
                return vid_id
        # Embed or Shorts
        for prefix in ("/embed/", "/shorts/", "/v/"):
            if parsed.path.startswith(prefix):
                vid_id = parsed.path[len(prefix):].split("?")[0].split("/")[0]
                if len(vid_id) == 11:
                    return vid_id

    # Raw 11-char ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url

    return None


def _entries_to_text(entries) -> str:
    """Convert transcript entries (dict or object) to clean text."""
    parts = []
    for entry in entries:
        if isinstance(entry, dict):
            text = entry.get("text", "")
        else:
            text = getattr(entry, "text", "") or ""
        text = text.strip()
        if text:
            parts.append(text)
    full = " ".join(parts)
    full = re.sub(r"\[.*?\]", "", full)   # Remove [Music], [Applause] etc
    full = re.sub(r"\s+", " ", full).strip()
    return full


def get_transcript(video_id: str) -> tuple[str, str]:
    """
    Fetch the transcript for a YouTube video.
    Tries new API (instance-based) first, falls back to old API (class method).

    Returns:
        (transcript_text, language_used)

    Raises:
        ValueError with a user-friendly message on failure.
    """
    try:
        # ── New API: youtube-transcript-api >= 0.7.0 ──────────────────────────
        api = YouTubeTranscriptApi()
        fetch_fn = getattr(api, "fetch", None)
        if fetch_fn:
            try:
                entries = list(fetch_fn(video_id, languages=["en"]))
                lang = "en"
            except Exception:
                try:
                    entries = list(fetch_fn(video_id))
                    lang = "auto"
                except Exception:
                    raise

            text = _entries_to_text(entries)
            if text:
                return text, lang

    except Exception:
        pass

    try:
        # ── Old API: youtube-transcript-api < 0.7.0 ───────────────────────────
        get_fn = getattr(YouTubeTranscriptApi, "get_transcript", None)
        if get_fn:
            try:
                entries = get_fn(video_id, languages=["en"])
                lang = "en"
            except Exception:
                entries = get_fn(video_id)
                lang = "auto"

            text = _entries_to_text(entries)
            if text:
                return text, lang

    except Exception:
        pass

    try:
        # ── Fallback: list all transcripts and fetch first available ──────────
        list_fn = getattr(YouTubeTranscriptApi, "list_transcripts", None)
        if list_fn:
            transcript_list = list_fn(video_id)
            for t in transcript_list:
                try:
                    entries = list(t.fetch())
                    text = _entries_to_text(entries)
                    if text:
                        return text, t.language_code
                except Exception:
                    continue

    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")

    raise ValueError(
        "No transcript found. The video may have captions disabled, "
        "be private, or unavailable in your region."
    )


def get_video_metadata(url: str) -> dict:
    """Returns basic metadata derivable without a YouTube API key."""
    video_id = extract_video_id(url)
    if not video_id:
        return {}
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
    }
