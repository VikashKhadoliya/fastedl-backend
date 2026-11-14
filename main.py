"""
Root application entrypoint for Instagram Downloader backend.
Delegates to the modular backend package while maintaining complete backward compatibility.
"""
from backend.main import app
from backend.routes.api import DownloadRequest, validate_url, health_check

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
