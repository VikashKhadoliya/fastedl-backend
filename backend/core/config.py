import os
from typing import List

class Settings:
    PROJECT_NAME: str = "FastEDL API"
    FULL_NAME: str = "Fast Easy Download Link"
    TAGLINE: str = "Download. Save. Enjoy."
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # CORS configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://fastedl.app",
        "*"
    ]

    # Timeouts & Limits
    REQUEST_TIMEOUT_SECONDS: int = 20
    MAX_DOWNLOAD_SIZE_BYTES: int = 250 * 1024 * 1024  # 250 MB
    CHUNK_SIZE: int = 1024 * 64  # 64 KB streaming chunks

    # Allowed hostnames for download proxy to prevent SSRF
    ALLOWED_DOWNLOAD_DOMAINS: List[str] = [
        "cdninstagram.com",
        "fbcdn.net",
        "instagram.com",
    ]

settings = Settings()
