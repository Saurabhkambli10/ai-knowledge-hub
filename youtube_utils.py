"""
YouTube transcript extraction utilities.
Uses youtube-transcript-api (free, no API key required).
Handles all versions of the library with multiple fallback strategies.
"""

import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str | None:
    url = url.strip()
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)
    parsed = urlparse(url)
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            params = parse_qs(parsed.query)
            vid_id = params.get("v", [None])[0]
            if vid_id:
                return vid_id
        for prefix in ("/embed/", "/shorts/", "/v/"):
            if parsed.path.startswith(prefix):
                vid_id = parsed.path[len(prefix):].split("?")[0].split("/")[0]
                if len(vid_id) == 11:
                    return vid_id
    if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
        return url
    return None


def _to_text(entries) -> str:
    """Convert transcript entries (dict or object) to clean plain text."""
    parts = []
    for e in entries:
        if isinstance(e, dict):
            t = e.get("text", "")
        else:
            t = getattr(e, "text", "") or ""
        t = t.strip()
        if t:
            parts.append(t)
    text = " ".join(parts)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_transcript(video_id: str) -> tuple[str, str]:
    """
    Fetch transcript using every available strategy.
    Returns (text, language_code).
    """
    last_error = "Unknown error"

    # ── Strategy 1: New instance API — api.list() then fetch each ────────────
    try:
        api = YouTubeTranscriptApi()
        list_fn = getattr(api, "list", None)
        if list_fn:
            tlist = list_fn(video_id)
            transcripts = list(tlist)
            # Prefer English, then any generated, then any manual
            ordered = sorted(
                transcripts,
                key=lambda t: (
                    0 if getattr(t, "language_code", "").startswith("en") else 1,
                    0 if getattr(t, "is_generated", True) else 1,
                )
            )
            for t in ordered:
                try:
                    fetched = t.fetch()
                    text = _to_text(list(fetched))
                    if text:
                        return text, getattr(t, "language_code", "auto")
                except Exception as e:
                    last_error = str(e)
                    continue
    except Exception as e:
        last_error = str(e)

    # ── Strategy 2: New instance API — api.fetch() directly ──────────────────
    try:
        api = YouTubeTranscriptApi()
        fetch_fn = getattr(api, "fetch", None)
        if fetch_fn:
            fetched = fetch_fn(video_id)
            text = _to_text(list(fetched))
            if text:
                return text, "auto"
    except Exception as e:
        last_error = str(e)

    # ── Strategy 3: Old class method — get_transcript ────────────────────────
    try:
        get_fn = getattr(YouTubeTranscriptApi, "get_transcript", None)
        if get_fn:
            entries = get_fn(video_id)
            text = _to_text(entries)
            if text:
                return text, "auto"
    except Exception as e:
        last_error = str(e)

    # ── Strategy 4: Old class method — list_transcripts ──────────────────────
    try:
        list_fn = getattr(YouTubeTranscriptApi, "list_transcripts", None)
        if list_fn:
            tlist = list_fn(video_id)
            for t in tlist:
                try:
                    text = _to_text(list(t.fetch()))
                    if text:
                        return text, getattr(t, "language_code", "auto")
                except Exception as e:
                    last_error = str(e)
                    continue
    except Exception as e:
        last_error = str(e)

    raise ValueError(
        f"Could not fetch transcript (last error: {last_error}). "
        "Make sure the video has captions enabled and is publicly accessible."
    )


def get_video_metadata(url: str) -> dict:
    video_id = extract_video_id(url)
    if not video_id:
        return {}
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
    }
