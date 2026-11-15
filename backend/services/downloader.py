import os
import uuid
import logging
import shutil
import requests
import subprocess
import tempfile
from typing import Generator, Optional, List
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from backend.core.config import settings
from backend.core.security import is_safe_external_url, sanitize_filename

logger = logging.getLogger(__name__)

def stream_media(
    media_url: str,
    filename: str,
    audio_url: Optional[str] = None,
    quality: Optional[str] = None,
    format_id: Optional[str] = None
) -> StreamingResponse:
    """
    Safely proxies media from Instagram/Meta CDNs to the browser as a downloadable attachment.
    Protects against SSRF, limits file size, and enforces timeouts.
    If audio_url is provided, seamlessly merges separate video and audio streams using FFmpeg.
    """
    if audio_url:
        return merge_and_stream_ffmpeg(media_url, audio_url, filename)

    if not is_safe_external_url(media_url):
        raise HTTPException(
            status_code=400,
            detail="Forbidden download target. Only official Instagram/Meta CDN URLs are permitted."
        )

    safe_name = sanitize_filename(filename, default="fastedl_download")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/",
        "Accept": "*/*",
    }

    try:
        upstream_resp = requests.get(
            media_url,
            headers=headers,
            stream=True,
            timeout=settings.REQUEST_TIMEOUT_SECONDS
        )

        if upstream_resp.status_code != 200:
            raise HTTPException(
                status_code=upstream_resp.status_code,
                detail="Upstream media source returned an error. Link may have expired."
            )

        content_type = upstream_resp.headers.get("Content-Type", "application/octet-stream")
        content_length_hdr = upstream_resp.headers.get("Content-Length")

        if content_length_hdr:
            try:
                content_len = int(content_length_hdr)
                if content_len > settings.MAX_DOWNLOAD_SIZE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Media file exceeds maximum allowed download size of {settings.MAX_DOWNLOAD_SIZE_BYTES // (1024*1024)}MB."
                    )
            except ValueError:
                pass

        def chunk_generator() -> Generator[bytes, None, None]:
            bytes_streamed = 0
            try:
                for chunk in upstream_resp.iter_content(chunk_size=settings.CHUNK_SIZE):
                    if not chunk:
                        continue
                    bytes_streamed += len(chunk)
                    if bytes_streamed > settings.MAX_DOWNLOAD_SIZE_BYTES:
                        logger.warning(f"Download aborted: file exceeded size limit ({bytes_streamed} bytes)")
                        break
                    yield chunk
            finally:
                upstream_resp.close()

        response_headers = {
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        if content_length_hdr:
            response_headers["Content-Length"] = content_length_hdr

        return StreamingResponse(
            chunk_generator(),
            media_type=content_type,
            headers=response_headers
        )

    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Media download timed out while connecting to Instagram CDN."
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Download streaming error: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve media from upstream server."
        )


def merge_and_stream_ffmpeg(video_url: str, audio_url: str, filename: str) -> StreamingResponse:
    """
    Downloads separate DASH video and audio streams to temp storage,
    losslessly merges them using FFmpeg (-c:v copy -c:a aac), and streams the result.
    Guarantees cleanup of all temporary artifacts.
    """
    if not is_safe_external_url(video_url) or not is_safe_external_url(audio_url):
        raise HTTPException(
            status_code=400,
            detail="Forbidden download target. Only official Instagram/Meta CDN URLs are permitted."
        )

    safe_name = sanitize_filename(filename, default="fastedl_video.mp4")
    if not safe_name.lower().endswith(".mp4"):
        safe_name += ".mp4"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.instagram.com/",
        "Accept": "*/*",
    }

    temp_id = uuid.uuid4().hex[:8]
    temp_dir = tempfile.gettempdir()
    video_tmp = os.path.join(temp_dir, f"fastedl_v_{temp_id}.mp4")
    audio_tmp = os.path.join(temp_dir, f"fastedl_a_{temp_id}.m4a")
    output_tmp = os.path.join(temp_dir, f"fastedl_merged_{temp_id}.mp4")

    temp_files = [video_tmp, audio_tmp, output_tmp]

    try:
        # Download video stream
        with requests.get(video_url, headers=headers, stream=True, timeout=settings.REQUEST_TIMEOUT_SECONDS) as r:
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail="Failed to fetch video stream from CDN")
            with open(video_tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=settings.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

        # Download audio stream
        with requests.get(audio_url, headers=headers, stream=True, timeout=settings.REQUEST_TIMEOUT_SECONDS) as r:
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail="Failed to fetch audio stream from CDN")
            with open(audio_tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=settings.CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

        # Run FFmpeg to merge video and audio without re-encoding video stream
        ffmpeg_bin = shutil.which("ffmpeg")
        merge_success = False

        if ffmpeg_bin:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-i", video_tmp,
                "-i", audio_tmp,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                "-movflags", "+faststart",
                output_tmp
            ]
            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
                if proc.returncode == 0 and os.path.exists(output_tmp) and os.path.getsize(output_tmp) > 0:
                    merge_success = True
                else:
                    err_msg = proc.stderr.decode(errors='ignore') if proc.stderr else "Unknown error"
                    logger.warning(f"FFmpeg merge exited with code {proc.returncode}: {err_msg[:300]}")
            except Exception as ffmpeg_err:
                logger.warning(f"FFmpeg process execution failed: {ffmpeg_err}")
        else:
            logger.warning("FFmpeg binary not detected on system. Falling back to video stream.")

        # If merge was successful, stream output_tmp; otherwise stream video_tmp
        stream_target = output_tmp if (merge_success and os.path.exists(output_tmp)) else video_tmp

        if not os.path.exists(stream_target) or os.path.getsize(stream_target) == 0:
            raise HTTPException(status_code=502, detail="Downloaded media stream is empty or corrupt")

        file_size = os.path.getsize(stream_target)

        def cleanup_stream():
            try:
                with open(stream_target, "rb") as f:
                    while True:
                        chunk = f.read(settings.CHUNK_SIZE)
                        if not chunk:
                            break
                        yield chunk
            finally:
                for tmp_file in temp_files:
                    try:
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                    except Exception:
                        pass

        response_headers = {
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Content-Length": str(file_size),
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Expose-Headers": "Content-Disposition, Content-Length"
        }

        return StreamingResponse(
            cleanup_stream(),
            media_type="video/mp4",
            headers=response_headers
        )

    except Exception as e:
        for tmp_file in temp_files:
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except Exception:
                pass
        if isinstance(e, HTTPException):
            raise
        logger.error(f"Error during media download/stream: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process video stream")
