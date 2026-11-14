import logging
import json
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from backend.db.database import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content", tags=["content"])

class ContactFormRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str

class TrackUsageRequest(BaseModel):
    tool_name: str

@router.get("/articles")
def get_published_articles(
    section: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT id, slug, section, title, excerpt, category, author, read_time, featured, created_at, updated_at FROM articles WHERE status = 'published'"
    params = []

    if section:
        query += " AND section = ?"
        params.append(section)

    if category:
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR excerpt LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY featured DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    articles = [dict(r) for r in cursor.fetchall()]

    # Get total count
    count_query = "SELECT COUNT(*) as total FROM articles WHERE status = 'published'"
    count_params = []
    if section:
        count_query += " AND section = ?"
        count_params.append(section)
    if category:
        count_query += " AND category = ?"
        count_params.append(category)
    if search:
        count_query += " AND (title LIKE ? OR excerpt LIKE ?)"
        count_params.extend([f"%{search}%", f"%{search}%"])

    cursor.execute(count_query, count_params)
    total = cursor.fetchone()["total"]

    conn.close()

    return {
        "success": True,
        "articles": articles,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/articles/{slug}")
def get_article_by_slug(slug: str, section: Optional[str] = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()

    if section:
        cursor.execute("SELECT * FROM articles WHERE slug = ? AND section = ? AND status = 'published'", (slug.strip().lower(), section))
    else:
        cursor.execute("SELECT * FROM articles WHERE slug = ? AND status = 'published'", (slug.strip().lower(),))
    
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Article not found")

    article = dict(row)
    if article.get("faq_json"):
        try:
            article["faqs"] = json.loads(article["faq_json"])
        except Exception:
            article["faqs"] = []
    else:
        article["faqs"] = []

    # Get related articles in same section or category
    cursor.execute("""
        SELECT id, slug, section, title, excerpt, category, read_time, created_at
        FROM articles
        WHERE (category = ? OR section = ?) AND slug != ? AND status = 'published'
        ORDER BY id DESC LIMIT 4
    """, (article["category"], article.get("section", "instagram-captions"), article["slug"]))
    related = [dict(r) for r in cursor.fetchall()]

    conn.close()

    return {
        "success": True,
        "article": article,
        "related": related
    }

@router.get("/categories")
def get_public_categories(section: Optional[str] = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()

    if section:
        cursor.execute("""
            SELECT c.*, COUNT(a.id) as article_count
            FROM categories c
            LEFT JOIN articles a ON a.category = c.slug AND a.status = 'published'
            WHERE c.section = ?
            GROUP BY c.id
            ORDER BY c.id ASC
        """, (section,))
    else:
        cursor.execute("""
            SELECT c.*, COUNT(a.id) as article_count
            FROM categories c
            LEFT JOIN articles a ON a.category = c.slug AND a.status = 'published'
            GROUP BY c.id
            ORDER BY c.id ASC
        """)

    categories = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"success": True, "categories": categories}

@router.post("/contact")
def submit_contact_message(data: ContactFormRequest, request: Request):
    """
    Submits user feedback/contact inquiry into persistent database for admin review.
    """
    client_ip = request.client.host if request.client else "unknown"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contact_messages (name, email, subject, message, status, ip_address, created_at)
        VALUES (?, ?, ?, ?, 'unread', ?, ?)
    """, (
        data.name.strip(),
        data.email.strip().lower(),
        data.subject.strip(),
        data.message.strip(),
        client_ip,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Thank you for reaching out. Our support team will review your message shortly."
    }

@router.get("/pages/{slug}")
def get_public_page_by_slug(slug: str):
    """
    Retrieves a published CMS page by its URL slug.
    Draft pages are never exposed to the public.
    """
    clean_slug = slug.strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pages WHERE slug = ? AND status = 'published'", (clean_slug,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Page not found or is currently in draft mode.")

    page = dict(row)
    return {
        "success": True,
        "page": page
    }

@router.post("/track")
def track_tool_usage(data: TrackUsageRequest):
    """
    Tracks anonymous usage metric for analytics dashboard.
    """
    tool_key = re.sub(r"[^a-zA-Z0-9_-]", "", data.tool_name.strip().lower())
    if not tool_key:
        return {"success": False}

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tool_analytics (tool_name, usage_count, last_used)
        VALUES (?, 1, ?)
        ON CONFLICT(tool_name) DO UPDATE SET
            usage_count = usage_count + 1,
            last_used = excluded.last_used
    """, (tool_key, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

    return {"success": True}
