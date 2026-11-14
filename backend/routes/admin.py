import logging
import os
import uuid
import shutil
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File, Form
from pydantic import BaseModel
from backend.db.database import get_db_connection, verify_password, hash_password
from backend.core.auth import create_access_token, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", "uploads", "media"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Request Models ---

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class ArticleCreateRequest(BaseModel):
    slug: str
    title: str
    section: Optional[str] = "instagram-captions"
    excerpt: str
    content: str
    category: str
    author: Optional[str] = "FastEDL Editorial Team"
    status: Optional[str] = "published"
    tags: Optional[str] = ""
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    read_time: Optional[str] = "5 min read"
    featured: Optional[int] = 0
    faq_json: Optional[str] = None

class ArticleUpdateRequest(BaseModel):
    title: Optional[str] = None
    section: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    read_time: Optional[str] = None
    featured: Optional[int] = None
    faq_json: Optional[str] = None

class CategoryRequest(BaseModel):
    slug: str
    name: str
    section: Optional[str] = "instagram-captions"
    description: Optional[str] = None
    icon: Optional[str] = "guide"

class CaptionCollectionRequest(BaseModel):
    category: str
    language: str = "en"
    length: str = "medium"
    caption_text: str
    tags: Optional[str] = ""

class HashtagCollectionRequest(BaseModel):
    category: str
    niche: str
    hashtags: str
    relevance_tier: Optional[str] = "high"

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, str]

# --- Page Management Models ---

class PageCreateRequest(BaseModel):
    slug: str
    title: str
    main_heading: Optional[str] = None
    subheading: Optional[str] = None
    content: str
    featured_image: Optional[str] = None
    category: Optional[str] = "general"
    author: Optional[str] = "FastEDL Editorial Team"
    status: Optional[str] = "published"
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    robots: Optional[str] = "index, follow"

class PageUpdateRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    main_heading: Optional[str] = None
    subheading: Optional[str] = None
    content: Optional[str] = None
    featured_image: Optional[str] = None
    category: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    canonical_url: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    og_image: Optional[str] = None
    robots: Optional[str] = None
    version_note: Optional[str] = None

class MediaUpdateRequest(BaseModel):
    alt_text: str

# --- Admin Auth Endpoint ---

@router.post("/login")
def admin_login(data: AdminLoginRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_users WHERE username = ?", (data.username.strip(),))
    user = cursor.fetchone()
    conn.close()

    if not user or not verify_password(data.password, user["password_hash"], user["salt"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin username or password"
        )

    token = create_access_token(user["username"], role=user["role"])
    return {
        "success": True,
        "token": token,
        "username": user["username"],
        "role": user["role"]
    }

@router.get("/me")
def get_current_admin_info(admin: dict = Depends(get_current_admin)):
    return {
        "success": True,
        "username": admin["sub"],
        "role": admin["role"]
    }

# --- Analytics Dashboard ---

@router.get("/analytics")
def get_dashboard_analytics(admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM articles")
    total_articles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM articles WHERE status = 'published'")
    published_articles = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM pages")
    total_pages = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM pages WHERE status = 'published'")
    published_pages = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM media_assets")
    total_media = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM contact_messages")
    total_messages = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM contact_messages WHERE status = 'unread'")
    unread_messages = cursor.fetchone()["total"]

    cursor.execute("SELECT tool_name, usage_count, last_used FROM tool_analytics ORDER BY usage_count DESC LIMIT 10")
    tool_usage = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, name, email, subject, created_at, status FROM contact_messages ORDER BY id DESC LIMIT 5")
    recent_messages = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "success": True,
        "stats": {
            "total_articles": total_articles,
            "published_articles": published_articles,
            "total_pages": total_pages,
            "published_pages": published_pages,
            "total_media": total_media,
            "total_messages": total_messages,
            "unread_messages": unread_messages,
        },
        "tool_usage": tool_usage,
        "recent_messages": recent_messages
    }

# --- Articles Management ---

@router.get("/articles")
def list_admin_articles(
    status_filter: Optional[str] = Query(None),
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM articles WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM articles ORDER BY id DESC")
    articles = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "articles": articles}

@router.post("/articles")
def create_article(data: ArticleCreateRequest, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM articles WHERE slug = ?", (data.slug.strip(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="An article with this slug already exists.")

    now_iso = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO articles (
            slug, title, section, excerpt, content, category, author, status,
            tags, seo_title, seo_description, read_time, featured, faq_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.slug.strip().lower(), data.title, data.section or "instagram-captions",
        data.excerpt, data.content,
        data.category, data.author or "FastEDL Editorial Team",
        data.status or "published", data.tags, data.seo_title or data.title,
        data.seo_description or data.excerpt, data.read_time or "5 min read",
        data.featured or 0, data.faq_json, now_iso, now_iso
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return {"success": True, "message": "Article published successfully", "article_id": new_id}

@router.put("/articles/{article_id}")
def update_article(
    article_id: int,
    data: ArticleUpdateRequest,
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM articles WHERE id = ?", (article_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Article not found")

    fields_to_update = {}
    for field, val in data.model_dump(exclude_unset=True).items():
        if val is not None:
            fields_to_update[field] = val

    if fields_to_update:
        fields_to_update["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        cursor.execute(f"UPDATE articles SET {set_clause} WHERE id = ?", (*fields_to_update.values(), article_id))
        conn.commit()

    conn.close()
    return {"success": True, "message": "Article updated successfully"}

@router.delete("/articles/{article_id}")
def delete_article(article_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Article deleted successfully"}

# --- Categories Management ---

@router.get("/categories")
def list_categories(admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY id ASC")
    cats = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "categories": cats}

@router.post("/categories")
def create_category(data: CategoryRequest, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (slug, name, section, description, icon) VALUES (?, ?, ?, ?, ?)",
            (data.slug.strip().lower(), data.name.strip(), data.section or "instagram-captions", data.description, data.icon or "guide")
        )
        conn.commit()
    except Exception:
        conn.close()
        raise HTTPException(status_code=400, detail="Category slug already exists")
    conn.close()
    return {"success": True, "message": "Category created"}

# ==============================================================
# --- PAGES MANAGEMENT SYSTEM (Core & Custom Pages) ---
# ==============================================================

@router.get("/pages")
def list_admin_pages(
    status_filter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, slug, title, main_heading, subheading, category, author, status, is_system, seo_title, updated_at, published_at FROM pages WHERE 1=1"
    params = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)

    if search:
        query += " AND (title LIKE ? OR slug LIKE ? OR main_heading LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " ORDER BY is_system DESC, id ASC"
    cursor.execute(query, params)
    pages = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "pages": pages}

@router.get("/pages/{page_id}")
def get_admin_page(page_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Page not found")

    page = dict(row)

    # Fetch version snapshots
    cursor.execute("SELECT id, title, created_at, version_note FROM page_versions WHERE page_id = ? ORDER BY id DESC LIMIT 10", (page_id,))
    versions = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {"success": True, "page": page, "versions": versions}

@router.post("/pages")
def create_admin_page(data: PageCreateRequest, admin: dict = Depends(get_current_admin)):
    clean_slug = data.slug.strip().lower().replace(" ", "-")
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM pages WHERE slug = ?", (clean_slug,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="A page with this URL slug already exists.")

    now_iso = datetime.utcnow().isoformat()
    pub_iso = now_iso if data.status == "published" else None

    cursor.execute("""
        INSERT INTO pages (
            slug, title, main_heading, subheading, content, featured_image,
            category, author, status, is_system, seo_title, seo_description,
            focus_keyword, canonical_url, og_title, og_description, og_image,
            robots, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean_slug, data.title.strip(), data.main_heading or data.title, data.subheading,
        data.content, data.featured_image, data.category or "general",
        data.author or "FastEDL Editorial Team", data.status or "published",
        data.seo_title or data.title, data.seo_description, data.focus_keyword,
        data.canonical_url, data.og_title or data.title, data.og_description,
        data.og_image, data.robots or "index, follow", now_iso, now_iso, pub_iso
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return {"success": True, "message": "Page created successfully", "page_id": new_id}

@router.put("/pages/{page_id}")
def update_admin_page(
    page_id: int,
    data: PageUpdateRequest,
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pages WHERE id = ?", (page_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="Page not found")

    existing_dict = dict(existing)
    now_iso = datetime.utcnow().isoformat()

    # Save a version snapshot of current state before updating
    snapshot_meta = json.dumps({
        "seo_title": existing_dict.get("seo_title"),
        "seo_description": existing_dict.get("seo_description"),
        "focus_keyword": existing_dict.get("focus_keyword"),
        "canonical_url": existing_dict.get("canonical_url"),
        "robots": existing_dict.get("robots")
    })
    cursor.execute("""
        INSERT INTO page_versions (page_id, title, content, seo_metadata_json, created_at, version_note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        page_id, existing_dict["title"], existing_dict["content"],
        snapshot_meta, now_iso, data.version_note or "Pre-update snapshot"
    ))

    fields_to_update = {}
    for field, val in data.model_dump(exclude_unset=True).items():
        if field == "version_note":
            continue
        if val is not None:
            if field == "slug":
                clean_slug = str(val).strip().lower().replace(" ", "-")
                # Check uniqueness if slug changed
                cursor.execute("SELECT id FROM pages WHERE slug = ? AND id != ?", (clean_slug, page_id))
                if cursor.fetchone():
                    conn.close()
                    raise HTTPException(status_code=400, detail="Slug already in use by another page.")
                fields_to_update["slug"] = clean_slug
            else:
                fields_to_update[field] = val

    fields_to_update["updated_at"] = now_iso

    # Handle published_at timestamp
    if fields_to_update.get("status") == "published" and not existing_dict.get("published_at"):
        fields_to_update["published_at"] = now_iso

    if fields_to_update:
        set_clause = ", ".join([f"{k} = ?" for k in fields_to_update.keys()])
        cursor.execute(f"UPDATE pages SET {set_clause} WHERE id = ?", (*fields_to_update.values(), page_id))
        conn.commit()

    conn.close()
    return {"success": True, "message": "Page updated successfully"}

@router.delete("/pages/{page_id}")
def delete_admin_page(page_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, slug, is_system FROM pages WHERE id = ?", (page_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Page not found")

    cursor.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Page deleted successfully"}

# ==============================================================
# --- MEDIA ASSETS & UPLOAD LIBRARY ---
# ==============================================================

ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}

@router.post("/media/upload")
async def upload_media_asset(
    file: UploadFile = File(...),
    alt_text: str = Form(""),
    admin: dict = Depends(get_current_admin)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image file format '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_IMAGE_EXTS))}"
        )

    # Generate safe unique filename
    safe_base = "".join(c for c in os.path.splitext(file.filename)[0] if c.isalnum() or c in ("-", "_")).rstrip()
    if not safe_base:
        safe_base = "media"
    unique_name = f"{safe_base}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)

    # Read and save file
    content_bytes = await file.read()
    file_size = len(content_bytes)

    if file_size > 15 * 1024 * 1024:  # 15MB limit
        raise HTTPException(status_code=400, detail="File size exceeds the 15MB limit.")

    with open(dest_path, "wb") as f:
        f.write(content_bytes)

    relative_url = f"/uploads/media/{unique_name}"
    mime_type = file.content_type or f"image/{ext.replace('.', '')}"
    now_iso = datetime.utcnow().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO media_assets (filename, file_path, file_size, mime_type, alt_text, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (file.filename, relative_url, file_size, mime_type, alt_text.strip(), now_iso))
    conn.commit()
    asset_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "asset": {
            "id": asset_id,
            "filename": file.filename,
            "url": relative_url,
            "file_size": file_size,
            "mime_type": mime_type,
            "alt_text": alt_text.strip(),
            "uploaded_at": now_iso
        }
    }

@router.get("/media")
def list_media_assets(
    search: Optional[str] = Query(None),
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    if search:
        cursor.execute("""
            SELECT * FROM media_assets
            WHERE filename LIKE ? OR alt_text LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cursor.execute("SELECT * FROM media_assets ORDER BY id DESC")

    assets = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "assets": assets}

@router.put("/media/{asset_id}")
def update_media_asset(
    asset_id: int,
    data: MediaUpdateRequest,
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE media_assets SET alt_text = ? WHERE id = ?", (data.alt_text.strip(), asset_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Alt text updated successfully"}

@router.delete("/media/{asset_id}")
def delete_media_asset(asset_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM media_assets WHERE id = ?", (asset_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Media asset not found")

    rel_path = row["file_path"].lstrip("/")
    # File is in frontend/public/
    full_disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "public", rel_path))
    if os.path.exists(full_disk_path):
        try:
            os.remove(full_disk_path)
        except Exception as e:
            logger.warning(f"Failed to remove file from disk: {e}")

    cursor.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Media asset deleted successfully"}

# --- Contact Messages Management ---

@router.get("/messages")
def list_contact_messages(
    status_filter: Optional[str] = Query(None),
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM contact_messages WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM contact_messages ORDER BY id DESC")
    messages = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "messages": messages}

@router.put("/messages/{message_id}")
def update_message_status(
    message_id: int,
    status: str = Query(..., pattern="^(read|replied|unread)$"),
    admin: dict = Depends(get_current_admin)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE contact_messages SET status = ? WHERE id = ?", (status, message_id))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Message status set to {status}"}

@router.delete("/messages/{message_id}")
def delete_contact_message(message_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact_messages WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Message deleted"}

# --- Settings Management ---

@router.get("/settings")
def get_site_settings(admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM site_settings")
    settings_dict = {r["key"]: r["value"] for r in cursor.fetchall()}
    conn.close()
    return {"success": True, "settings": settings_dict}

@router.put("/settings")
def update_site_settings(data: SettingsUpdateRequest, admin: dict = Depends(get_current_admin)):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.utcnow().isoformat()
    for k, v in data.settings.items():
        cursor.execute("""
            INSERT INTO site_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """, (k, v, now_iso))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Settings updated successfully"}
