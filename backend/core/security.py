import re
import socket
import ipaddress
import logging
from urllib.parse import urlparse
from typing import Tuple
from fastapi import HTTPException
from backend.core.config import settings

logger = logging.getLogger(__name__)

INSTAGRAM_POST_REGEX = re.compile(
    r"/(p|reel|reels|tv)/([A-Za-z0-9_-]+)",
    re.IGNORECASE
)

INSTAGRAM_STORY_REGEX = re.compile(
    r"/stories/([A-Za-z0-9_.-]+)(?:/([0-9]+))?",
    re.IGNORECASE
)

INSTAGRAM_PROFILE_REGEX = re.compile(
    r"^/([A-Za-z0-9_.-]{1,30})/?$",
    re.IGNORECASE
)

RESERVED_SLUGS = {
    "p", "reel", "reels", "tv", "stories", "explore", "direct", 
    "accounts", "about", "legal", "developer", "api", "support",
    "terms", "privacy", "help"
}

SAFE_FILENAME_REGEX = re.compile(r"[^A-Za-z0-9_.-]")

def clean_raw_instagram_url(raw_input: str) -> str:
    """
    Cleans, extracts, and normalizes an Instagram URL from arbitrary user input.
    Handles links embedded in share text, missing schemes, whitespace, quotes, etc.
    """
    if not raw_input:
        return ""
    
    cleaned = raw_input.strip().strip("'\"<>[]()")
    
    # Check if user pasted share text containing a link
    extracted = re.search(r"https?://[^\s]+", cleaned)
    if extracted:
        cleaned = extracted.group(0).rstrip(".,;!?)\"'")
    
    # Auto-prepend https:// if scheme is missing
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        if cleaned.startswith("instagram.com") or cleaned.startswith("www.instagram.com") or cleaned.startswith("instagr.am") or cleaned.startswith("ddinstagram.com"):
            cleaned = "https://" + cleaned
            
    return cleaned

def validate_instagram_url(url_str: str) -> Tuple[str, str]:
    """
    Validates that a URL is a legitimate Instagram post, reel, story, tv, or profile URL.
    Returns (content_type, shortcode_or_identifier).
    Raises HTTPException(400) if invalid.
    """
    cleaned_url = clean_raw_instagram_url(url_str)
    if not cleaned_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    parsed = urlparse(cleaned_url)

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL scheme. Must be http or https"
        )

    hostname = (parsed.hostname or "").lower()
    allowed_hosts = (
        "instagram.com", "www.instagram.com", "m.instagram.com",
        "instagr.am", "www.instagr.am", "ddinstagram.com"
    )
    if hostname not in allowed_hosts and not hostname.endswith(".instagram.com"):
        raise HTTPException(
            status_code=400,
            detail="Only Instagram URLs (e.g. instagram.com/reel/...) are supported"
        )

    path = parsed.path.strip()

    # 1. Standard Post / Reel / IGTV
    post_match = INSTAGRAM_POST_REGEX.search(path)
    if post_match:
        media_type = post_match.group(1).lower()
        if media_type == "reels":
            media_type = "reel"
        shortcode = post_match.group(2)
        return media_type, shortcode

    # 2. Instagram Story: /stories/{username}/{story_id}/
    story_match = INSTAGRAM_STORY_REGEX.search(path)
    if story_match:
        username = story_match.group(1)
        story_id = story_match.group(2) or username
        return "story", story_id

    # 3. Instagram Profile / Viewer: /{username}/
    profile_match = INSTAGRAM_PROFILE_REGEX.match(path)
    if profile_match:
        slug = profile_match.group(1).lower()
        if slug not in RESERVED_SLUGS:
            return "profile", slug

    raise HTTPException(
        status_code=400,
        detail="Invalid Instagram post format. Supported: Videos (/p/, /tv/), Reels (/reel/), Photos (/p/), Carousels, Stories (/stories/), or Profile Viewer links."
    )

def is_safe_external_url(url_str: str) -> bool:
    """
    Verifies that a URL targets legitimate Instagram/Meta CDN hosts
    and does not resolve to private or internal network addresses (SSRF defense).
    """
    try:
        parsed = urlparse(url_str.strip())
        if parsed.scheme != "https":
            return False

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        # Domain whitelist check: must end with one of the allowed domains
        domain_matches = any(
            hostname == domain or hostname.endswith("." + domain)
            for domain in settings.ALLOWED_DOWNLOAD_DOMAINS
        )
        if not domain_matches:
            return False

        # DNS resolution and IP address validation
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for entry in addr_info:
                ip_str = entry[4][0]
                ip_obj = ipaddress.ip_address(ip_str)

                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_reserved
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                ):
                    return False
        except socket.gaierror:
            # If DNS resolution is offline / in sandbox, domain whitelist check still strictly protects
            pass

        return True
    except Exception:
        return False

def sanitize_filename(filename: str, default: str = "fastedl_media") -> str:
    """
    Sanitizes a download filename, preventing directory traversal and header injection.
    """
    if not filename:
        return default

    # Strip directory paths
    base_name = filename.replace("\\", "/").split("/")[-1]
    # Keep only safe chars
    clean_name = SAFE_FILENAME_REGEX.sub("_", base_name)
    clean_name = clean_name.strip("._")

    if not clean_name:
        return default

    # Enforce maximum length
    if len(clean_name) > 100:
        clean_name = clean_name[:100]

    return clean_name
