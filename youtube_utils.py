"""
YouTube transcript extraction utilities.
Uses youtube-transcript-api (free, no API key required).
"""

import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


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


def get_transcript(video_id: str) -> tuple[str, str]:
    """
    Fetch the transcript for a YouTube video.

    Returns:
        (transcript_text, language_used)

    Raises:
        ValueError with a user-friendly message on failure.
    """
    try:
        # Try English first, then fall back to any available language
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
            lang = "en"
        except NoTranscriptFound:
            # Get whatever is available
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_obj = transcripts.find_manually_created_transcript(
                [t.language_code for t in transcripts]
            ) if any(True for _ in transcripts._manually_created_transcripts.values()) else \
                transcripts.find_generated_transcript(
                [t.language_code for t in transcripts]
            )
            transcript_list = transcript_obj.fetch()
            lang = transcript_obj.language_code

        # Join all segments into clean text
        full_text = " ".join(
            entry["text"].strip()
            for entry in transcript_list
            if entry.get("text", "").strip()
        )
        # Clean up common transcript artifacts
        full_text = re.sub(r"\[.*?\]", "", full_text)   # Remove [Music], [Applause] etc
        full_text = re.sub(r"\s+", " ", full_text).strip()

        return full_text, lang

    except TranscriptsDisabled:
        raise ValueError(
            "Transcripts are disabled for this video. The creator has turned off captions."
        )
    except VideoUnavailable:
        raise ValueError(
            "This video is unavailable (private, deleted, or region-restricted)."
        )
    except NoTranscriptFound:
        raise ValueError(
            "No transcript found for this video. Try a video with captions enabled."
        )
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")


def get_video_metadata(url: str) -> dict:
    """
    Returns basic metadata we can derive without an API key.
    For richer metadata (title, channel), users would need YouTube Data API.
    We return what we can for free.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {}
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "embed_url": f"https://www.youtube.com/embed/{video_id}",
    }
