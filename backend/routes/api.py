import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from backend.core.security import validate_instagram_url
from backend.services.extractor import extract_media
from backend.services.downloader import stream_media, convert_and_stream_mp3

logger = logging.getLogger(__name__)

router = APIRouter()

class DownloadRequest(BaseModel):
    url: str

@router.get("/")
@router.get("/health")
def health_check():
    return {
        "status": "online",
        "app": "FastEDL",
        "full_name": "Fast Easy Download Link",
        "tagline": "Download. Save. Enjoy.",
        "message": "FastEDL API is operational",
        "features": {
            "reels": True,
            "videos": True,
            "photos": True,
            "carousels": True,
            "stream_proxy": True
        }
    }

@router.post("/validate")
def validate_url(data: DownloadRequest):
    """
    Validates an Instagram URL and returns the shortcode and media category.
    Preserves backward compatibility with existing API contracts.
    """
    url_str = str(data.url)
    media_type, shortcode = validate_instagram_url(url_str)

    return {
        "status": "valid",
        "app": "FastEDL",
        "type": media_type,
        "shortcode": shortcode,
        "message": "Instagram URL validated successfully"
    }

@router.post("/fetch")
def fetch_media(data: DownloadRequest):
    """
    Validates the Instagram URL and extracts metadata, thumbnails,
    and download URLs across reels, single posts, and carousels.
    """
    url_str = str(data.url)
    media_type, shortcode = validate_instagram_url(url_str)

    try:
        media_data = extract_media(url_str, shortcode, media_type)
        return media_data
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        logger.warning(f"Error fetching media for {url_str}: {error_message}")
        raise HTTPException(
            status_code=400,
            detail=error_message
        )

@router.get("/download")
def download_media(
    url: str = Query(..., description="Direct Instagram CDN media URL"),
    filename: Optional[str] = Query("fastedl_download", description="Target file name for download"),
    audio_url: Optional[str] = Query(None, description="Optional separate audio stream URL to merge with FFmpeg"),
    quality: Optional[str] = Query(None, description="Optional quality tier label"),
    format_id: Optional[str] = Query(None, description="Optional format ID identifier"),
    format: Optional[str] = Query(None, description="Optional output format ('mp3' or 'mp4')"),
    bitrate: Optional[int] = Query(192, description="Target MP3 bitrate in kbps (128, 192, 320)"),
    inline: Optional[bool] = Query(False, description="Set True for in-browser audio preview playback")
):
    """
    Streams media through backend proxy to bypass CORS restrictions
    and force attachment download in the user's browser.
    Automatically merges separate video and audio streams via FFmpeg if audio_url is specified.
    If format='mp3', converts audio stream to MP3 via FFmpeg.
    """
    return stream_media(
        url,
        filename,
        audio_url=audio_url,
        quality=quality,
        format_id=format_id,
        format=format,
        bitrate=bitrate,
        inline=inline
    )

@router.get("/download-mp3")
def download_mp3(
    url: str = Query(..., description="Direct Instagram CDN media or audio stream URL"),
    filename: Optional[str] = Query("fastedl_audio", description="Target file name for download"),
    bitrate: Optional[int] = Query(192, description="Target MP3 bitrate in kbps (128, 192, 320)"),
    audio_url: Optional[str] = Query(None, description="Optional separate direct audio stream URL"),
    inline: Optional[bool] = Query(False, description="Set True for in-browser audio preview playback")
):
    """
    Downloads an Instagram audio or video stream, extracts and converts audio to MP3 using FFmpeg,
    and returns a StreamingResponse with Content-Type: audio/mpeg and Content-Length.
    """
    target_url = audio_url or url
    return convert_and_stream_mp3(target_url, filename, bitrate=bitrate, inline=inline)
