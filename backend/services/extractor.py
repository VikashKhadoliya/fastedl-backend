import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
import instaloader
from instaloader.exceptions import (
    InstaloaderException,
    QueryReturnedNotFoundException,
    PrivateProfileNotFollowedException,
    LoginRequiredException,
    BadResponseException,
    ConnectionException,
)
import yt_dlp
from backend.core.config import settings

logger = logging.getLogger(__name__)

# Initialize a shared instaloader instance with appropriate limits
_instaloader_instance: Optional[instaloader.Instaloader] = None

def get_instaloader() -> instaloader.Instaloader:
    global _instaloader_instance
    if _instaloader_instance is None:
        _instaloader_instance = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            request_timeout=settings.REQUEST_TIMEOUT_SECONDS,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    return _instaloader_instance


def format_filesize(num_bytes: Optional[int]) -> Optional[str]:
    """Formats raw bytes into a human-readable string (e.g. 1.8 MB, 720 KB)."""
    if not num_bytes or num_bytes <= 0:
        return None
    val = float(num_bytes)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if val < 1024.0:
            return f"{val:.1f} {unit}" if unit in ('MB', 'GB') else f"{int(val)} {unit}"
        val /= 1024.0
    return f"{val:.1f} GB"


def normalize_quality_tier(qlabel_or_pval: Any) -> Tuple[str, str, int]:
    """
    Maps quality label or pixel value strictly to one of the 8 supported tiers:
    144p, 240p, 360p, 480p, 720p HD, 1080p Full HD, 1440p 2K, 2160p 4K.
    Strictly preserves source authenticity: never upscales or mislabels.
    """
    val = 0
    if isinstance(qlabel_or_pval, int):
        val = qlabel_or_pval
    elif isinstance(qlabel_or_pval, str):
        m = re.search(r"(\d+)", qlabel_or_pval)
        if m:
            val = int(m.group(1))

    if val >= 2160:
        return "2160p", "2160p 4K", 2160
    elif val >= 1440:
        return "1440p", "1440p 2K", 1440
    elif val >= 1080:
        return "1080p", "1080p Full HD", 1080
    elif val >= 720:
        return "720p", "720p HD", 720
    elif val >= 480:
        return "480p", "480p", 480
    elif val >= 360:
        return "360p", "360p", 360
    elif val >= 240:
        return "240p", "240p", 240
    elif val > 0:
        return "144p", "144p", 144
    else:
        return "original", "Original Quality", 720


def parse_dash_manifest(manifest_xml: str) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Parses video representations and best audio representation from video_dash_manifest XML.
    """
    if not manifest_xml or not isinstance(manifest_xml, str):
        return [], None

    try:
        root = ET.fromstring(manifest_xml)
    except Exception:
        return [], None

    ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""

    video_reps: List[Dict[str, Any]] = []
    audio_reps: List[Dict[str, Any]] = []

    for aset in root.findall(f".//{ns}AdaptationSet"):
        ctype = (aset.attrib.get("contentType") or aset.attrib.get("mimeType") or "").lower()
        if "audio" in ctype:
            for rep in aset.findall(f"{ns}Representation"):
                burl = rep.find(f"{ns}BaseURL")
                if burl is not None and burl.text:
                    url = burl.text.strip()
                    bw = int(rep.attrib.get("bandwidth") or rep.attrib.get("FBAvgBitrate") or 0)
                    length = int(rep.attrib.get("FBContentLength") or 0)
                    audio_reps.append({
                        "id": rep.attrib.get("id"),
                        "url": url,
                        "codecs": rep.attrib.get("codecs") or "mp4a",
                        "bandwidth": bw,
                        "filesize": length if length > 0 else None
                    })
        elif "video" in ctype:
            for rep in aset.findall(f"{ns}Representation"):
                burl = rep.find(f"{ns}BaseURL")
                if burl is not None and burl.text:
                    url = burl.text.strip()
                    qlabel = rep.attrib.get("FBQualityLabel")
                    w = int(rep.attrib.get("width") or 0)
                    h = int(rep.attrib.get("height") or 0)
                    codecs = rep.attrib.get("codecs") or "mp4"
                    length = int(rep.attrib.get("FBContentLength") or 0)
                    bw = int(rep.attrib.get("bandwidth") or 0)
                    video_reps.append({
                        "id": rep.attrib.get("id"),
                        "qlabel": qlabel,
                        "width": w if w > 0 else None,
                        "height": h if h > 0 else None,
                        "codecs": codecs,
                        "filesize": length if length > 0 else None,
                        "bandwidth": bw if bw > 0 else None,
                        "url": url
                    })

    best_audio = max(audio_reps, key=lambda a: a["bandwidth"]) if audio_reps else None
    return video_reps, best_audio


def build_all_video_qualities(
    video_dash_manifest: Optional[str] = None,
    video_versions: Optional[List[Dict[str, Any]]] = None,
    default_url: Optional[str] = None,
    orig_width: Optional[int] = None,
    orig_height: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Inspects all genuinely available formats:
    - DASH video representations (e.g. 1080p, 720p, 480p, 360p, 240p, 144p) paired with audio stream for FFmpeg merging.
    - Progressive video versions (native interleaved audio, zero remux needed).
    Returns all valid options sorted descending by resolution tier.
    """
    qualities_by_tier: Dict[str, Dict[str, Any]] = {}

    video_reps, best_audio = parse_dash_manifest(video_dash_manifest or "")
    audio_url = best_audio["url"] if best_audio else None

    # 1. Process DASH representations
    for rep in video_reps:
        qlabel_str = rep.get("qlabel")
        w = rep.get("width") or orig_width
        h = rep.get("height") or orig_height

        tier_id, tier_label, rank = normalize_quality_tier(qlabel_str or (min(w, h) if w and h else orig_height))
        res_str = f"{w}x{h}" if (w and h) else None
        dim_str = f"{w} × {h} px" if (w and h) else None
        fs = rep.get("filesize")
        fs_fmt = format_filesize(fs)

        if tier_id not in qualities_by_tier or (rep.get("bandwidth", 0) > qualities_by_tier[tier_id].get("_bw", 0)):
            qualities_by_tier[tier_id] = {
                "id": tier_id,
                "format_id": rep.get("id") or f"dash_{tier_id}",
                "label": tier_label,
                "resolution": res_str,
                "dimensions_label": dim_str,
                "width": w,
                "height": h,
                "codec": rep.get("codecs") or "mp4",
                "format": "MP4",
                "filesize": fs,
                "filesize_formatted": fs_fmt,
                "download_url": rep.get("url"),
                "audio_url": audio_url,
                "needs_merge": bool(audio_url),
                "rank": rank,
                "is_default": False,
                "_bw": rep.get("bandwidth", 0),
                "_has_native_audio": False
            }

    # 2. Process progressive video_versions (native audio included, zero merge needed!)
    if video_versions:
        for idx, v in enumerate(video_versions):
            v_url = v.get("url")
            if not v_url:
                continue
            w = v.get("width") or orig_width
            h = v.get("height") or orig_height
            p_val = min(w, h) if (w and h) else (orig_height or 720)
            tier_id, tier_label, rank = normalize_quality_tier(p_val)
            res_str = f"{w}x{h}" if (w and h) else None
            dim_str = f"{w} × {h} px" if (w and h) else None

            # If this tier already exists from DASH, prefer progressive stream for 720p/lower because it already has native audio!
            if tier_id in qualities_by_tier:
                existing = qualities_by_tier[tier_id]
                existing["download_url"] = v_url
                existing["audio_url"] = None
                existing["needs_merge"] = False
                existing["format_id"] = str(v.get("id") or f"prog_{tier_id}")
                existing["_has_native_audio"] = True
            else:
                qualities_by_tier[tier_id] = {
                    "id": tier_id,
                    "format_id": str(v.get("id") or f"prog_{tier_id}"),
                    "label": tier_label,
                    "resolution": res_str,
                    "dimensions_label": dim_str,
                    "width": w,
                    "height": h,
                    "codec": "h264",
                    "format": "MP4",
                    "filesize": None,
                    "filesize_formatted": None,
                    "download_url": v_url,
                    "audio_url": None,
                    "needs_merge": False,
                    "rank": rank,
                    "is_default": False,
                    "_bw": 0,
                    "_has_native_audio": True
                }

    # 3. Fallback to default_url if nothing extracted
    if not qualities_by_tier and default_url:
        p_val = min(orig_width, orig_height) if (orig_width and orig_height) else (orig_height or 720)
        tier_id, tier_label, rank = normalize_quality_tier(p_val)
        res_str = f"{orig_width}x{orig_height}" if (orig_width and orig_height) else None
        dim_str = f"{orig_width} × {orig_height} px" if (orig_width and orig_height) else None
        qualities_by_tier[tier_id] = {
            "id": tier_id,
            "format_id": "original_source",
            "label": tier_label,
            "resolution": res_str,
            "dimensions_label": dim_str,
            "width": orig_width,
            "height": orig_height,
            "codec": "mp4",
            "format": "MP4",
            "filesize": None,
            "filesize_formatted": None,
            "download_url": default_url,
            "audio_url": None,
            "needs_merge": False,
            "rank": rank,
            "is_default": True
        }

    sorted_qualities = sorted(qualities_by_tier.values(), key=lambda q: q["rank"], reverse=True)
    for q in sorted_qualities:
        q.pop("_bw", None)
        q.pop("_has_native_audio", None)

    if sorted_qualities:
        sorted_qualities[0]["is_default"] = True

    return sorted_qualities


def build_video_qualities_from_ytdlp(
    formats: List[Dict[str, Any]],
    default_url: Optional[str] = None,
    orig_width: Optional[int] = None,
    orig_height: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Builds structured quality options from yt-dlp formats array.
    Pairs video-only streams with the best available audio stream for FFmpeg remuxing.
    """
    qualities_by_tier: Dict[str, Dict[str, Any]] = {}

    audio_formats = [
        f for f in formats
        if f.get("acodec") and f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url")
    ]
    best_audio = max(
        audio_formats,
        key=lambda f: f.get("abr") or f.get("tbr") or 0
    ) if audio_formats else None
    best_audio_url = best_audio.get("url") if best_audio else None

    dash_video_formats = [
        f for f in formats
        if f.get("url") and f.get("vcodec") and f.get("vcodec") != "none" and f.get("acodec") == "none"
    ]
    prog_video_formats = [
        f for f in formats
        if f.get("url") and (
            (f.get("acodec") and f.get("acodec") != "none") or
            f.get("format_id") in ("1", "2", "3") or
            (f.get("ext") == "mp4" and f not in dash_video_formats)
        )
    ]

    dash_sorted = sorted(dash_video_formats, key=lambda f: f.get("tbr") or f.get("vbr") or 0)

    for f in dash_sorted:
        w = f.get("width") or orig_width
        h = f.get("height") or orig_height
        tbr = f.get("tbr") or f.get("vbr") or 0

        min_dim = min(w, h) if (w and h) else 0
        if min_dim >= 2160 or tbr >= 4500:
            tier_val = 2160
        elif min_dim >= 1440 or tbr >= 3000:
            tier_val = 1440
        elif min_dim >= 1080 or tbr >= 1600:
            tier_val = 1080
        elif min_dim >= 720 and tbr >= 950:
            tier_val = 720
        elif tbr >= 500:
            tier_val = 480
        elif tbr >= 300:
            tier_val = 360
        elif tbr >= 160:
            tier_val = 240
        else:
            tier_val = 144

        tier_id, tier_label, rank = normalize_quality_tier(tier_val)
        res_str = f"{w}x{h}" if (w and h) else None
        dim_str = f"{w} × {h} px" if (w and h) else None
        fs = f.get("filesize") or f.get("filesize_approx")
        fs_fmt = format_filesize(fs)

        if tier_id not in qualities_by_tier or (tbr > qualities_by_tier[tier_id].get("_tbr", 0)):
            qualities_by_tier[tier_id] = {
                "id": tier_id,
                "format_id": f.get("format_id") or f"ytdlp_{tier_id}",
                "label": tier_label,
                "resolution": res_str,
                "dimensions_label": dim_str,
                "width": w,
                "height": h,
                "codec": f.get("vcodec") or "mp4",
                "format": "MP4",
                "filesize": fs,
                "filesize_formatted": fs_fmt,
                "download_url": f.get("url"),
                "audio_url": best_audio_url,
                "needs_merge": bool(best_audio_url),
                "rank": rank,
                "is_default": False,
                "_tbr": tbr,
                "_has_native_audio": False
            }

    for pf in prog_video_formats:
        w = pf.get("width")
        h = pf.get("height")
        p_val = min(w, h) if (w and h) else 720
        tier_id, tier_label, rank = normalize_quality_tier(p_val)
        if tier_id in qualities_by_tier:
            qualities_by_tier[tier_id]["download_url"] = pf.get("url")
            qualities_by_tier[tier_id]["audio_url"] = None
            qualities_by_tier[tier_id]["needs_merge"] = False
            qualities_by_tier[tier_id]["_has_native_audio"] = True
        elif not qualities_by_tier:
            pw = w or orig_width
            ph = h or orig_height
            res_str = f"{pw}x{ph}" if (pw and ph) else None
            dim_str = f"{pw} × {ph} px" if (pw and ph) else None
            qualities_by_tier[tier_id] = {
                "id": tier_id,
                "format_id": pf.get("format_id") or f"ytdlp_prog_{tier_id}",
                "label": tier_label,
                "resolution": res_str,
                "dimensions_label": dim_str,
                "width": pw,
                "height": ph,
                "codec": "mp4",
                "format": "MP4",
                "filesize": pf.get("filesize"),
                "filesize_formatted": format_filesize(pf.get("filesize")),
                "download_url": pf.get("url"),
                "audio_url": None,
                "needs_merge": False,
                "rank": rank,
                "is_default": False,
                "_tbr": 0,
                "_has_native_audio": True
            }

    if not qualities_by_tier and default_url:
        p_val = min(orig_width, orig_height) if (orig_width and orig_height) else (orig_height or 720)
        tier_id, tier_label, rank = normalize_quality_tier(p_val)
        res_str = f"{orig_width}x{orig_height}" if (orig_width and orig_height) else None
        dim_str = f"{orig_width} × {orig_height} px" if (orig_width and orig_height) else None
        qualities_by_tier[tier_id] = {
            "id": tier_id,
            "format_id": "original_source",
            "label": tier_label,
            "resolution": res_str,
            "dimensions_label": dim_str,
            "width": orig_width,
            "height": orig_height,
            "codec": "mp4",
            "format": "MP4",
            "filesize": None,
            "filesize_formatted": None,
            "download_url": default_url,
            "audio_url": None,
            "needs_merge": False,
            "rank": rank,
            "is_default": True
        }

    sorted_qualities = sorted(qualities_by_tier.values(), key=lambda q: q["rank"], reverse=True)
    for q in sorted_qualities:
        q.pop("_tbr", None)
        q.pop("_has_native_audio", None)

    if sorted_qualities:
        sorted_qualities[0]["is_default"] = True

    return sorted_qualities


def extract_with_instaloader(shortcode: str, raw_type: str) -> Dict[str, Any]:
    """
    Primary extractor using Instaloader.
    Extracts high-resolution media, carousels, reels, videos, photos, and public profiles.
    """
    loader = get_instaloader()

    # Case: Public Profile / Anonymous Viewer
    if raw_type == "profile":
        profile = instaloader.Profile.from_username(loader.context, shortcode)
        if profile.is_private:
            raise PrivateProfileNotFollowedException("Private account")

        avatar_url = profile.profile_pic_url
        items = [{
            "index": 1,
            "type": "image",
            "format": "JPG",
            "thumbnail_url": avatar_url,
            "download_url": avatar_url,
            "filename": f"fastedl_avatar_{shortcode}.jpg"
        }]

        recent_posts = []
        try:
            count = 0
            for p in profile.get_posts():
                if count >= 6:
                    break
                recent_posts.append({
                    "shortcode": p.shortcode,
                    "type": "video" if p.is_video else "image",
                    "thumbnail_url": p.url,
                    "likes": p.likes,
                    "caption": (p.caption or "")[:120]
                })
                count += 1
        except Exception:
            pass

        return {
            "success": True,
            "source": "instaloader",
            "shortcode": shortcode,
            "type": "viewer",
            "caption": profile.biography or f"Instagram profile @{shortcode}",
            "full_caption": profile.biography or "",
            "owner": profile.username,
            "owner_avatar": avatar_url,
            "full_name": profile.full_name,
            "followers": profile.followers,
            "following": profile.followees,
            "media_count": profile.mediacount,
            "recent_posts": recent_posts,
            "total_items": len(items),
            "items": items
        }

    post = instaloader.Post.from_shortcode(loader.context, shortcode)

    caption = getattr(post, "caption", "") or ""
    owner = getattr(post, "owner_username", "") or ""
    owner_avatar = None
    try:
        if hasattr(post, "owner_profile") and post.owner_profile:
            owner_avatar = getattr(post.owner_profile, "profile_pic_url", None)
    except Exception:
        owner_avatar = None
    likes = getattr(post, "likes", 0)
    timestamp = post.date_utc.isoformat() if getattr(post, "date_utc", None) else None

    node_dict = getattr(post, "_node", {}) or {}
    orig_w = node_dict.get("original_width") or node_dict.get("dimensions", {}).get("width")
    orig_h = node_dict.get("original_height") or node_dict.get("dimensions", {}).get("height")
    carousel_media = node_dict.get("carousel_media", [])

    typename = getattr(post, "typename", "")
    items: List[Dict[str, Any]] = []

    # Case 1: Carousel / Sidecar
    if typename == "GraphSidecar":
        resolved_type = "carousel"
        for idx, node in enumerate(post.get_sidecar_nodes()):
            is_node_video = getattr(node, "is_video", False)
            cm_item = carousel_media[idx] if idx < len(carousel_media) else {}
            item_w = cm_item.get("original_width") or orig_w
            item_h = cm_item.get("original_height") or orig_h
            res_str = f"{item_w}x{item_h}" if (item_w and item_h) else None
            dim_label = f"{item_w} × {item_h} px" if (item_w and item_h) else None

            if is_node_video:
                video_url = getattr(node, "video_url", None)
                video_versions = cm_item.get("video_versions", [])
                dash_manifest = cm_item.get("video_dash_manifest")
                qualities = build_all_video_qualities(
                    video_dash_manifest=dash_manifest,
                    video_versions=video_versions,
                    default_url=video_url,
                    orig_width=item_w,
                    orig_height=item_h
                )
                best_dl = qualities[0]["download_url"] if (qualities and qualities[0].get("download_url")) else video_url

                items.append({
                    "index": idx + 1,
                    "type": "video",
                    "format": "MP4",
                    "thumbnail_url": getattr(node, "display_url", None),
                    "download_url": best_dl,
                    "filename": f"fastedl_{shortcode}_slide_{idx + 1}.mp4",
                    "width": item_w,
                    "height": item_h,
                    "resolution": res_str,
                    "dimensions_label": dim_label,
                    "qualities": qualities
                })
            else:
                img_url = getattr(node, "display_url", None)
                items.append({
                    "index": idx + 1,
                    "type": "image",
                    "format": "JPG",
                    "thumbnail_url": img_url,
                    "download_url": img_url,
                    "filename": f"fastedl_{shortcode}_slide_{idx + 1}.jpg",
                    "width": item_w,
                    "height": item_h,
                    "resolution": res_str,
                    "dimensions_label": dim_label
                })

    # Case 2: Video / Reel / IGTV
    elif post.is_video or typename == "GraphVideo":
        if raw_type == "reel":
            resolved_type = "reel"
        elif raw_type == "tv":
            resolved_type = "igtv"
        else:
            resolved_type = "video"

        video_url = post.video_url
        video_versions = node_dict.get("video_versions", [])
        dash_manifest = node_dict.get("video_dash_manifest")
        qualities = build_all_video_qualities(
            video_dash_manifest=dash_manifest,
            video_versions=video_versions,
            default_url=video_url,
            orig_width=orig_w,
            orig_height=orig_h
        )
        best_dl = qualities[0]["download_url"] if (qualities and qualities[0].get("download_url")) else video_url

        res_str = f"{orig_w}x{orig_h}" if (orig_w and orig_h) else None
        dim_label = f"{orig_w} × {orig_h} px" if (orig_w and orig_h) else None

        items.append({
            "index": 1,
            "type": "video",
            "format": "MP4",
            "thumbnail_url": post.url,
            "download_url": best_dl,
            "filename": f"fastedl_{shortcode}.mp4",
            "video_duration": getattr(post, "video_duration", None),
            "video_view_count": getattr(post, "video_view_count", None),
            "width": orig_w,
            "height": orig_h,
            "resolution": res_str,
            "dimensions_label": dim_label,
            "qualities": qualities
        })

    # Case 3: Single Image
    else:
        resolved_type = "photo"
        res_str = f"{orig_w}x{orig_h}" if (orig_w and orig_h) else None
        dim_label = f"{orig_w} × {orig_h} px" if (orig_w and orig_h) else None

        items.append({
            "index": 1,
            "type": "image",
            "format": "JPG",
            "thumbnail_url": post.url,
            "download_url": post.url,
            "filename": f"fastedl_{shortcode}.jpg",
            "width": orig_w,
            "height": orig_h,
            "resolution": res_str,
            "dimensions_label": dim_label
        })

    return {
        "success": True,
        "source": "instaloader",
        "shortcode": shortcode,
        "type": resolved_type,
        "caption": caption[:300] + ("..." if len(caption) > 300 else ""),
        "full_caption": caption,
        "owner": owner,
        "owner_avatar": owner_avatar,
        "likes": likes,
        "timestamp": timestamp,
        "total_items": len(items),
        "items": items
    }


def extract_with_ytdlp(url: str, shortcode: str, raw_type: str) -> Dict[str, Any]:
    """
    Fallback extractor using yt-dlp.
    Particularly strong for Instagram Reels, IGTV, and video posts.
    """
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": settings.REQUEST_TIMEOUT_SECONDS,
        "extract_flat": False,
        "noplaylist": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise Exception("yt-dlp could not extract metadata from this URL")

        # Check for multiple entries (carousel)
        entries = info.get("entries")
        items: List[Dict[str, Any]] = []

        if entries:
            resolved_type = "carousel"
            for idx, entry in enumerate(entries):
                if not entry:
                    continue
                ext = entry.get("ext", "mp4" if entry.get("vcodec") != "none" else "jpg")
                is_vid = entry.get("vcodec") != "none" or ext == "mp4"
                w = entry.get("width")
                h = entry.get("height")
                res_str = f"{w}x{h}" if (w and h) else None
                dim_label = f"{w} × {h} px" if (w and h) else None

                entry_formats = entry.get("formats", [])
                media_url = entry.get("url") or (entry_formats[-1].get("url") if entry_formats else None)
                thumb = entry.get("thumbnail") or media_url

                if is_vid:
                    qualities = build_video_qualities_from_ytdlp(
                        entry_formats,
                        default_url=media_url,
                        orig_width=w,
                        orig_height=h
                    )
                    best_dl = qualities[0]["download_url"] if qualities else media_url
                    items.append({
                        "index": idx + 1,
                        "type": "video",
                        "format": "MP4",
                        "thumbnail_url": thumb,
                        "download_url": best_dl,
                        "filename": f"fastedl_{shortcode}_slide_{idx + 1}.mp4",
                        "width": w,
                        "height": h,
                        "resolution": res_str,
                        "dimensions_label": dim_label,
                        "qualities": qualities
                    })
                else:
                    items.append({
                        "index": idx + 1,
                        "type": "image",
                        "format": "JPG",
                        "thumbnail_url": thumb,
                        "download_url": media_url,
                        "filename": f"fastedl_{shortcode}_slide_{idx + 1}.jpg",
                        "width": w,
                        "height": h,
                        "resolution": res_str,
                        "dimensions_label": dim_label
                    })
        else:
            ext = info.get("ext", "mp4")
            is_vid = info.get("vcodec") != "none" or ext == "mp4" or raw_type == "reel"
            resolved_type = raw_type if raw_type in ("reel", "video") else ("video" if is_vid else "photo")

            w = info.get("width")
            h = info.get("height")
            res_str = f"{w}x{h}" if (w and h) else None
            dim_label = f"{w} × {h} px" if (w and h) else None

            formats = info.get("formats", [])
            media_url = info.get("url")
            if not media_url and formats:
                for f in reversed(formats):
                    if f.get("url"):
                        media_url = f.get("url")
                        break

            thumb = info.get("thumbnail") or media_url

            if is_vid:
                qualities = build_video_qualities_from_ytdlp(
                    formats,
                    default_url=media_url,
                    orig_width=w,
                    orig_height=h
                )
                best_dl = qualities[0]["download_url"] if qualities else media_url

                items.append({
                    "index": 1,
                    "type": "video",
                    "format": "MP4",
                    "thumbnail_url": thumb,
                    "download_url": best_dl,
                    "filename": f"fastedl_{shortcode}.mp4",
                    "video_duration": info.get("duration"),
                    "width": w,
                    "height": h,
                    "resolution": res_str,
                    "dimensions_label": dim_label,
                    "qualities": qualities
                })
            else:
                items.append({
                    "index": 1,
                    "type": "image",
                    "format": "JPG",
                    "thumbnail_url": thumb,
                    "download_url": media_url,
                    "filename": f"fastedl_{shortcode}.jpg",
                    "width": w,
                    "height": h,
                    "resolution": res_str,
                    "dimensions_label": dim_label
                })

        caption = info.get("description") or info.get("title") or ""
        owner = info.get("uploader") or info.get("channel") or ""

        return {
            "success": True,
            "source": "yt-dlp",
            "shortcode": shortcode,
            "type": resolved_type,
            "caption": caption[:300] + ("..." if len(caption) > 300 else ""),
            "full_caption": caption,
            "owner": owner,
            "owner_avatar": None,
            "likes": info.get("like_count"),
            "timestamp": info.get("upload_date"),
            "total_items": len(items),
            "items": items
        }


def extract_media(url: str, shortcode: str, raw_type: str) -> Dict[str, Any]:
    """
    Multi-tiered extractor orchestrating Instaloader and yt-dlp.
    Handles privacy errors, rate limits, and unsupported content explicitly.
    """
    errors: List[str] = []

    # Attempt 1: Instaloader
    try:
        data = extract_with_instaloader(shortcode, raw_type)
        if data.get("items") and len(data["items"]) > 0:
            return data
    except PrivateProfileNotFollowedException:
        raise Exception(
            "This post is from a private Instagram account. To protect user privacy, content from private accounts cannot be accessed or downloaded."
        )
    except LoginRequiredException:
        errors.append("Instagram requested login authentication.")
    except QueryReturnedNotFoundException:
        raise Exception(
            "The requested Instagram post or reel could not be found. It may have been deleted, archived, or made private."
        )
    except Exception as e:
        logger.warning(f"Instaloader failed for {shortcode}: {str(e)}")
        errors.append(f"Instaloader: {str(e)}")

    # Attempt 2: yt-dlp fallback
    try:
        data = extract_with_ytdlp(url, shortcode, raw_type)
        if data.get("items") and len(data["items"]) > 0:
            return data
    except Exception as e:
        err_msg = str(e).lower()
        logger.warning(f"yt-dlp failed for {shortcode}: {str(e)}")
        if "private" in err_msg or "login" in err_msg:
            raise Exception(
                "This post is from a private account or requires an active Instagram login. We do not bypass platform access controls."
            )
        errors.append(f"yt-dlp: {str(e)}")

    # If both failed, analyze reasons and provide clear response
    if raw_type == "story":
        raise Exception(
            "Instagram Stories are ephemeral (available for only 24 hours) and require authentication. Please ensure the account is public and the story is currently active."
        )

    combined_errors = "; ".join(errors)
    if "rate limit" in combined_errors.lower() or "429" in combined_errors:
        raise Exception(
            "Instagram is temporarily rate-limiting requests. Please try again in 1-2 minutes."
        )

    raise Exception(
        "Unable to retrieve media from this Instagram link. The post may be restricted, private, age-gated, or Instagram has updated their anti-scraping policies."
    )
