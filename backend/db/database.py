import sqlite3
import os
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "fastedl.db")

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    )
    return dk.hex(), salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    dk, _ = hash_password(password, salt)
    return dk == password_hash

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Admin Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL
    )
    """)

    # 2. Categories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        section TEXT NOT NULL DEFAULT 'instagram-captions',
        description TEXT,
        icon TEXT DEFAULT 'guide'
    )
    """)

    # Ensure section column exists in categories
    try:
        cursor.execute("ALTER TABLE categories ADD COLUMN section TEXT DEFAULT 'instagram-captions'")
    except sqlite3.OperationalError:
        pass

    # 3. Articles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        section TEXT NOT NULL DEFAULT 'instagram-captions',
        category TEXT NOT NULL,
        excerpt TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT NOT NULL DEFAULT 'FastEDL Editorial Team',
        status TEXT NOT NULL DEFAULT 'published',
        tags TEXT,
        seo_title TEXT,
        seo_description TEXT,
        read_time TEXT DEFAULT '5 min read',
        featured INTEGER DEFAULT 0,
        faq_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # Ensure section column exists in articles
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN section TEXT DEFAULT 'instagram-captions'")
    except sqlite3.OperationalError:
        pass

    # 4. Caption Collections Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS caption_collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        language TEXT NOT NULL DEFAULT 'en',
        length TEXT NOT NULL DEFAULT 'medium',
        caption_text TEXT NOT NULL,
        tags TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 5. Hashtag Collections Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hashtag_collections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        niche TEXT NOT NULL,
        hashtags TEXT NOT NULL,
        relevance_tier TEXT DEFAULT 'high',
        created_at TEXT NOT NULL
    )
    """)

    # 6. Contact Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'unread',
        ip_address TEXT,
        created_at TEXT NOT NULL
    )
    """)

    # 7. Site Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS site_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 8. Tool Analytics Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tool_analytics (
        tool_name TEXT PRIMARY KEY,
        usage_count INTEGER NOT NULL DEFAULT 0,
        last_used TEXT NOT NULL
    )
    """)

    # 9. Pages Table (Complete Page Management System)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        main_heading TEXT,
        subheading TEXT,
        content TEXT NOT NULL,
        featured_image TEXT,
        category TEXT DEFAULT 'general',
        author TEXT DEFAULT 'FastEDL Editorial Team',
        status TEXT NOT NULL DEFAULT 'published',
        is_system INTEGER DEFAULT 0,
        seo_title TEXT,
        seo_description TEXT,
        focus_keyword TEXT,
        canonical_url TEXT,
        og_title TEXT,
        og_description TEXT,
        og_image TEXT,
        robots TEXT DEFAULT 'index, follow',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        published_at TEXT
    )
    """)

    # 10. Page Versions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS page_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        seo_metadata_json TEXT,
        created_at TEXT NOT NULL,
        version_note TEXT
    )
    """)

    # 11. Media Assets Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS media_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER NOT NULL,
        mime_type TEXT NOT NULL,
        alt_text TEXT DEFAULT '',
        uploaded_at TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed Default Admin (admin / FastEDL@Admin2026!) if not present
    cursor.execute("SELECT id FROM admin_users WHERE username = 'admin'")
    if not cursor.fetchone():
        p_hash, salt = hash_password("FastEDL@Admin2026!")
        cursor.execute("""
            INSERT INTO admin_users (username, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, 'admin', ?)
        """, ("admin", p_hash, salt, datetime.utcnow().isoformat()))
        logger.info("Initialized default admin user: admin")

    # Seed Default Settings
    default_settings = {
        "site_name": "FastEDL",
        "site_tagline": "Download. Create. Grow.",
        "announcement": "",
        "maintenance_mode": "false",
        "contact_email": "support@fastedl.app",
        "max_download_size_mb": "250",
    }
    for k, v in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO site_settings (key, value, updated_at) VALUES (?, ?, ?)",
                       (k, v, datetime.utcnow().isoformat()))

    # Seed Content Library Categories
    content_categories = [
        # --- Instagram Captions ---
        ("mood-captions", "Mood Captions", "instagram-captions", "Captions reflecting daily emotions, vibes, and states of mind.", "smile"),
        ("attitude-captions", "Attitude Captions", "instagram-captions", "Confident, bold, and unapologetic captions for high impact.", "star"),
        ("love-captions", "Love Captions", "instagram-captions", "Romantic and heartfelt captions for couples and sweethearts.", "heart"),
        ("funny-captions", "Funny Captions", "instagram-captions", "Witty, humorous, and relatable captions that spark laughs.", "smile"),
        ("self-love-captions", "Self-Love Captions", "instagram-captions", "Empowering quotes and affirmations celebrating self-growth.", "heart"),
        ("travel-captions", "Travel Captions", "instagram-captions", "Wanderlust quotes and adventure captions for explorers.", "plane"),
        ("birthday-captions", "Birthday Captions", "instagram-captions", "Celebratory captions for milestone birthdays and parties.", "star"),
        ("friendship-captions", "Friendship Captions", "instagram-captions", "Heartwarming captions dedicated to best friends and squads.", "smile"),
        ("aesthetic-captions", "Aesthetic Captions", "instagram-captions", "Minimalist, poetic, and artful captions for curate grids.", "photo"),
        ("sad-captions", "Sad Captions", "instagram-captions", "Melancholy, honest, and reflective captions for vulnerable moments.", "help"),
        ("mirror-selfie-captions", "Mirror Selfie Captions", "instagram-captions", "Effortless one-liners for outfit checks and mirror snaps.", "photo"),

        # --- Instagram Hashtags ---
        ("fashion-hashtags", "Fashion Hashtags", "instagram-hashtags", "Targeted tag groups for OOTD, luxury, and street style.", "fashion"),
        ("travel-hashtags", "Travel Hashtags", "instagram-hashtags", "Curated travel tags to amplify reach on Instagram Explore.", "plane"),
        ("fitness-hashtags", "Fitness Hashtags", "instagram-hashtags", "Workout, bodybuilding, and wellness tags with high engagement.", "fitness"),
        ("photography-hashtags", "Photography Hashtags", "instagram-hashtags", "Niche tags for portrait, landscape, and street photographers.", "photo"),
        ("business-hashtags", "Business Hashtags", "instagram-hashtags", "Entrepreneurship, marketing, and small business tags.", "business"),
        ("food-hashtags", "Food Hashtags", "instagram-hashtags", "Foodie, recipe, and restaurant tags that drive local discovery.", "food"),

        # --- Instagram Bios ---
        ("boys-instagram-bios", "Boys Instagram Bios", "instagram-bio-ideas", "Stylish, VIP, attitude, and simple bios for boys.", "star"),
        ("girls-instagram-bios", "Girls Instagram Bios", "instagram-bio-ideas", "Aesthetic, classy, cute, and boss-babe bios for girls.", "heart"),
        ("attitude-bios", "Attitude Bios", "instagram-bio-ideas", "Bold, unapologetic, and punchy bios that demand respect.", "star"),
        ("business-bios", "Business Bios", "instagram-bio-ideas", "Professional, converting bios with clear value and calls to action.", "business"),
        ("creator-bios", "Creator Bios", "instagram-bio-ideas", "Engaging bios tailored for influencers, artists, and creators.", "photo"),

        # --- Instagram Ideas ---
        ("instagram-reel-ideas", "Instagram Reel Ideas", "instagram-ideas", "Viral video hooks, trending concepts, and audio transitions.", "reels"),
        ("instagram-post-ideas", "Instagram Post Ideas", "instagram-ideas", "High-retention carousel blueprints, prompts, and photos.", "copy-tool"),
        ("instagram-story-ideas", "Instagram Story Ideas", "instagram-ideas", "Interactive story stickers, polls, and Q&A formats.", "gif"),
    ]

    for slug, name, section, desc, icon in content_categories:
        cursor.execute("INSERT OR REPLACE INTO categories (slug, name, section, description, icon) VALUES (?, ?, ?, ?, ?)",
                       (slug, name, section, desc, icon))

    # Seed Initial Manually-Curated Master Articles
    initial_content_articles = [
        # 1. Mood Captions
        {
            "slug": "mood-instagram-captions",
            "section": "instagram-captions",
            "category": "mood-captions",
            "title": "120+ Best Mood Captions for Instagram in 2026 (Copy & Paste)",
            "excerpt": "Looking for the perfect mood caption? Browse 120+ hand-picked Instagram captions for every vibe—from chill and low-key to energetic, grateful, and introspective.",
            "author": "FastEDL Editorial Team",
            "read_time": "6 min read",
            "featured": 1,
            "seo_title": "120+ Best Mood Instagram Captions (Copy & Paste Lists)",
            "seo_description": "Copy the best mood captions for Instagram. Curated list of short, aesthetic, chill, and emotional quotes with one-click copy buttons.",
            "faq_json": json.dumps([
                {"q": "What makes a great mood caption on Instagram?", "a": "A great mood caption directly complements the tone of your photo without over-explaining. Short, relatable phrases that capture an emotional state generally perform best."},
                {"q": "How can I copy these captions to my clipboard?", "a": "Simply tap the 'Copy' button beside any individual caption, or use the 'Copy All' button at the top of each section to grab the entire list at once."},
                {"q": "Should I add hashtags to my mood captions?", "a": "Yes, 3 to 5 relevant tags like #CurrentMood or #VibeCheck help Instagram classify your post without cluttering your aesthetic."}
            ]),
            "content": """
<p class="lead">Whether you're feeling on top of the world, quietly reflective, or enjoying an afternoon with zero responsibilities, matching your Instagram post with the exact right mood caption makes all the difference.</p>

<p>Below you'll find our hand-curated library of <strong>over 120 mood captions for Instagram</strong>, organized by specific emotion. Use the individual <strong>Copy</strong> buttons to grab your favorite instantly, or tap <strong>Copy All</strong> to save an entire group for later.</p>

<h2>Chill & Low-Key Mood Captions</h2>
<p>For cozy mornings, quiet weekends, or those candid moments when life feels calm and centered.</p>

<ul class="caption-group" data-title="Chill & Low-Key Mood Captions">
  <li>Too blessed to be stressed. ✨</li>
  <li>Quiet mind, peaceful soul, warm coffee. ☕</li>
  <li>Living in soft focus today. 🌿</li>
  <li>Current status: off the clock and unapologetic.</li>
  <li>Finding joy in the simplest quiet corners. 📖</li>
  <li>Slowing down to match my peace.</li>
  <li>Less perfection, more genuine connection. ☁️</li>
  <li>In my own lane, at my own pace. 🧘</li>
</ul>

<h2>High Energy & Unstoppable Vibes</h2>
<p>When you are feeling confident, accomplished, and ready to take over the world.</p>

<ul class="caption-group" data-title="High Energy & Unstoppable Vibes">
  <li>Operating strictly on ambition and good energy. ⚡</li>
  <li>Proof that hard work looks good on you. 🔥</li>
  <li>Main character energy: permanently enabled. 🎬</li>
  <li>Not where I want to be yet, but light years from where I started. 🚀</li>
  <li>Big dreams, clear vision, zero excuses. 🏆</li>
  <li>Turning doubts into milestones since day one.</li>
  <li>Stay humble, work hungry. 💪</li>
</ul>

<h2>Silly, Witty & Playful Moods</h2>
<p>Lighthearted one-liners that don't take social media too seriously.</p>

<ul class="caption-group" data-title="Silly, Witty & Playful Moods">
  <li>I followed my heart, and it led me straight to the fridge. 🍕</li>
  <li>Mentally on a beach with zero unread emails. 🏖️</li>
  <li>My mood depends entirely on how my hair behaves today. 😂</li>
  <li>Reality called, so I hung up. 📵</li>
  <li>I put the 'pro' in procrastinate. ✨</li>
  <li>Don't study me, you won't graduate. 🎓</li>
</ul>

<h2>Thoughtful & Reflective Moods</h2>
<p>Poetic and vulnerable captions for sunset shots, journal entries, and personal milestones.</p>

<ul class="caption-group" data-title="Thoughtful & Reflective Moods">
  <li>Healing isn't linear, but peace is worth every chapter. 🌊</li>
  <li>You don't need everyone to understand your journey, just respect it.</li>
  <li>Sunsets are proof that endings can be beautiful too. 🌅</li>
  <li>Grateful for where I am, excited for where I'm going. 🧭</li>
  <li>The strongest people aren't those who show strength, but those who win battles we know nothing about. 🕊️</li>
</ul>
"""
        },

        # 2. Attitude Captions
        {
            "slug": "attitude-captions",
            "section": "instagram-captions",
            "category": "attitude-captions",
            "title": "80+ Savage Attitude Captions for Instagram (Boys & Girls)",
            "excerpt": "Looking to add confidence and swagger to your Instagram posts? Explore 80+ savage, bold, and high-status attitude captions with instant copy buttons.",
            "author": "FastEDL Editorial Team",
            "read_time": "5 min read",
            "featured": 1,
            "seo_title": "80+ Savage Attitude Instagram Captions (Bold & Confident)",
            "seo_description": "Best attitude captions for Instagram boys & girls. Copy savage one-liners, boss quotes, and classy attitude captions with 1-click.",
            "faq_json": json.dumps([
                {"q": "How do I choose the best attitude caption?", "a": "Choose an attitude caption that matches your natural tone. Short, punchy one-liners with bold statements usually get the highest comment and save rates."},
                {"q": "Can I use these attitude captions for Instagram Reels?", "a": "Absolutely. Attitude one-liners make excellent hook overlays for trending audio and transition Reels."}
            ]),
            "content": """
<p class="lead">A great attitude post needs a caption that commands attention without trying too hard. Whether you're dropping a gym transformation, a tailored outfit check, or a fresh selfie, your words should carry weight.</p>

<p>Here is our curated collection of <strong>80+ savage attitude captions</strong>, built with instant one-click copy buttons.</p>

<h2>Classy & Unapologetic Attitude Captions</h2>
<p>Understated confidence that speaks for itself without shouting.</p>

<ul class="caption-group" data-title="Classy Attitude Captions">
  <li>Silent moves, loud results. ♟️</li>
  <li>I am not a second choice. Either pick me or watch me walk. 🚪</li>
  <li>Excellence isn't an act, it's a habit. 👑</li>
  <li>Never chase what you can replace. 💎</li>
  <li>They talk behind your back because you're already two steps ahead. 🚶‍♂️</li>
  <li>Polite to everyone, close to few, dependent on none. 🛡️</li>
  <li>Class is knowing what to say, when to say it, and when to stop. 🥂</li>
</ul>

<h2>Savage & Sharp One-Liners</h2>
<p>Bold statements for when you want your comments section to light up.</p>

<ul class="caption-group" data-title="Savage One-Liners">
  <li>Know your worth, then add tax. 📈</li>
  <li>I don't hold grudges, I hold standards. 🎯</li>
  <li>You couldn't handle me even if I came with instructions. ⚠️</li>
  <li>I don't compete for spots I already own. 🥇</li>
  <li>My vibe is not everyone's cup of tea, and I drink espresso anyway. ☕</li>
  <li>Not arrogant, just self-aware of what I bring to the table. 💼</li>
</ul>
"""
        },

        # 3. Travel Captions
        {
            "slug": "travel-captions",
            "section": "instagram-captions",
            "category": "travel-captions",
            "title": "75+ Wanderlust Travel Captions for Instagram Adventures",
            "excerpt": "Capture the thrill of the open road, mountain vistas, and coastal escapes with 75+ short, poetic, and inspiring Instagram travel captions.",
            "author": "FastEDL Editorial Team",
            "read_time": "5 min read",
            "featured": 1,
            "seo_title": "75+ Best Travel Instagram Captions (Wanderlust & Adventure)",
            "seo_description": "Copy the best travel captions for Instagram. Short wanderlust quotes, scenic sunset lines, and airport check-ins with 1-click copy.",
            "faq_json": json.dumps([
                {"q": "What travel captions get the most saves?", "a": "Captions that share destination tips, hidden gems, or actionable location advice receive significantly more saves and shares."},
                {"q": "Should I include location tags in travel captions?", "a": "Always tag the city or region in Instagram's location sticker for discoverability, and mention the spot in the opening line."}
            ]),
            "content": """
<p class="lead">Nothing beats the feeling of stepping off an airplane into a new city or reaching a mountain summit at sunrise. Give your travel photos and drone Reels the captions they deserve.</p>

<h2>Short & Punchy Wanderlust Lines</h2>
<p>Clean, minimal captions that let breathtaking views speak for themselves.</p>

<ul class="caption-group" data-title="Short Wanderlust Lines">
  <li>Lost in the right direction. 🧭</li>
  <li>Passport full of stamps, heart full of memories. ✈️</li>
  <li>Catch flights, not feelings. 🛫</li>
  <li>Another pin dropped on the map. 📍</li>
  <li>Wander often, wonder always. 🌍</li>
  <li>Chasing sunsets across different timezones. 🌅</li>
  <li>Finding paradise wherever the compass points. 🏝️</li>
  <li>Out of office indefinitely. 📴</li>
</ul>

<h2>Scenic Nature & Adventure Captions</h2>
<p>For hiking trails, coastal drives, and remote wilderness retreats.</p>

<ul class="caption-group" data-title="Nature & Adventure Captions">
  <li>The mountains were calling, so I left town. 🏔️</li>
  <li>Salt water cures almost everything. 🌊</li>
  <li>Between the trees and under the stars. 🌲✨</li>
  <li>Nature never hurries, yet everything gets accomplished. 🍃</li>
  <li>Muddy boots, clear mind, full heart. 🥾</li>
  <li>Take only memories, leave only footprints. 🐾</li>
</ul>
"""
        },

        # 4. Travel Hashtags
        {
            "slug": "travel-hashtags",
            "section": "instagram-hashtags",
            "category": "travel-hashtags",
            "title": "Best Travel Hashtags for Instagram to Boost Explore Reach",
            "excerpt": "A researched breakdown of top-tier travel hashtags categorized by destination, solo travel, luxury retreats, and photography.",
            "author": "FastEDL Editorial Team",
            "read_time": "5 min read",
            "featured": 1,
            "seo_title": "Best Travel Hashtags for Instagram 2026 (Copy & Paste Sets)",
            "seo_description": "Boost your Instagram travel reach. Copy high-engagement travel hashtag sets for solo travel, luxury trips, and landscape photography.",
            "faq_json": json.dumps([
                {"q": "How many travel hashtags should I paste?", "a": "Use 5 to 8 targeted tags from the relevant niche list below for optimal algorithm classification."},
                {"q": "Do hashtags still work on travel Reels?", "a": "Yes! Hashtags tell Instagram's recommendation engine who should see your travel video on their Explore and Reels feed."}
            ]),
            "content": """
<p class="lead">Using giant hashtags like #travel or #wanderlust gets your posts buried within seconds. The secret to consistent reach is using targeted, medium-volume tags that match your exact destination and travel style.</p>

<h2>General Travel & Discovery Tags</h2>
<p>Medium-density tags that attract active travelers and travel communities.</p>

<ul class="caption-group" data-title="General Travel Discovery">
  <li>#TravelMoments #PassportReady #RoamThePlanet</li>
  <li>#ExploreEverywhere #TravelCommunity #WanderlustVibes</li>
  <li>#TravelStories #ScenicViews #TravelMoreOften</li>
  <li>#WorldTraveler #PostcardsFromTheWorld #TravelAddicted</li>
</ul>

<h2>Solo Travel & Adventure Tags</h2>
<p>For solo adventurers, backpacking journeys, and off-the-beaten-path expeditions.</p>

<ul class="caption-group" data-title="Solo Travel Tags">
  <li>#SoloTravelDiaries #AdventureSeeker #BackpackingLife</li>
  <li>#SoloTravelerStories #WildernessCulture #ExploreWild</li>
  <li>#GoExplore #TrailLife #IntoTheWild</li>
</ul>
"""
        },

        # 5. Boys Instagram Bio Ideas
        {
            "slug": "boys-instagram-bio",
            "section": "instagram-bio-ideas",
            "category": "boys-instagram-bios",
            "title": "120+ Cool & Aesthetic Instagram Bios for Boys (VIP & Stylish)",
            "excerpt": "Upgrade your Instagram profile with 120+ unique bios for boys. From minimalist and confident to VIP attitude and classy quotes.",
            "author": "FastEDL Editorial Team",
            "read_time": "5 min read",
            "featured": 1,
            "seo_title": "120+ Cool Instagram Bios for Boys (Aesthetic & VIP Lists)",
            "seo_description": "Best Instagram bio ideas for boys. Copy aesthetic, attitude, minimal, and VIP bio templates with one click.",
            "faq_json": json.dumps([
                {"q": "What is the character limit for an Instagram bio?", "a": "Instagram bios have a strict 150-character limit. Keep it concise, punchy, and include a clear link or call to action."},
                {"q": "Can I use custom fonts in my bio?", "a": "Yes! You can format your bio text using FastEDL's Caption Formatter tool to add bold or aesthetic script symbols."}
            ]),
            "content": """
<p class="lead">Your Instagram bio is your personal landing page. Visitors decide whether to tap 'Follow' within 3 seconds of scanning your bio, profile picture, and grid.</p>

<p>Here are <strong>over 120 stylish Instagram bios for boys</strong> that make a lasting impression.</p>

<h2>Classy & Minimalist Bios</h2>
<p>Short, confident bios that leave an aura of mystery.</p>

<ul class="caption-group" data-title="Classy Minimalist Bios">
  <li>Simple life, elevated standards. ☕</li>
  <li>Quiet confidence > Loud insecurities. ♟️</li>
  <li>Building silently. Let results speak. 🏗️</li>
  <li>Less talking, more execution. 🎯</li>
  <li>Driven by passion, guided by discipline. ⚡</li>
  <li>Living in the real world, posting occasionally. 🌐</li>
</ul>

<h2>VIP Attitude & Ambition Bios</h2>
<p>For ambitious creators, entrepreneurs, and fitness athletes.</p>

<ul class="caption-group" data-title="VIP & Ambition Bios">
  <li>Turning coffee into capital since day one. 💼</li>
  <li>Discipline over motivation. Every single day. 💪</li>
  <li>Mastering the craft. 🚀</li>
  <li>Born to express, not to impress. 👑</li>
  <li>Chasing horizons others are afraid to look at. 🧭</li>
  <li>Obsessed with progress, indifferent to applause. 🏆</li>
</ul>
"""
        }
    ]

    for art in initial_content_articles:
        cursor.execute("SELECT id FROM articles WHERE slug = ?", (art["slug"],))
        existing = cursor.fetchone()
        now_iso = datetime.utcnow().isoformat()
        if not existing:
            cursor.execute("""
                INSERT INTO articles (
                    slug, section, category, title, excerpt, content,
                    author, status, seo_title, seo_description, read_time,
                    featured, faq_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?)
            """, (
                art["slug"], art["section"], art["category"], art["title"],
                art["excerpt"], art["content"], art["author"], art["seo_title"],
                art["seo_description"], art["read_time"], art["featured"],
                art["faq_json"], now_iso, now_iso
            ))
        else:
            # Update existing with proper section & curated content
            cursor.execute("""
                UPDATE articles
                SET section = ?, category = ?, title = ?, excerpt = ?, content = ?,
                    seo_title = ?, seo_description = ?, read_time = ?, featured = ?,
                    faq_json = ?, updated_at = ?
                WHERE slug = ?
            """, (
                art["section"], art["category"], art["title"], art["excerpt"],
                art["content"], art["seo_title"], art["seo_description"],
                art["read_time"], art["featured"], art["faq_json"], now_iso,
                art["slug"]
            ))

    # Seed Initial Editable Pages (10 Core System Pages)
    initial_pages = [
        {
            "slug": "home",
            "title": "Home Page",
            "main_heading": "Fast Easy Download Link — Download. Save. Enjoy.",
            "subheading": "The fastest, most secure online utility to preview and download Instagram media in pristine original quality.",
            "category": "core",
            "is_system": 1,
            "seo_title": "FastEDL - Fast & Free Instagram Downloader (Videos, Reels, Photos)",
            "seo_description": "Download Instagram videos, reels, photos, stories and carousels in original 1080p Full HD quality. Fast, private and 100% free.",
            "focus_keyword": "Instagram Downloader",
            "canonical_url": "https://fastedl.app",
            "og_title": "FastEDL - Fast & Free Instagram Downloader",
            "og_description": "Download Instagram videos, reels, photos, stories and carousels in original 1080p Full HD quality.",
            "content": """<h2>Welcome to FastEDL</h2><p class="lead">Fast Easy Download Link (FastEDL) is the premier web-based media extractor designed specifically for Instagram creators, social media managers, and digital archivists.</p><h3>Why Choose FastEDL?</h3><ul><li><strong>Genuine Quality:</strong> We extract source video ladders up to 1080p Full HD with direct AAC stereo audio muxing.</li><li><strong>Zero Quality Upscaling:</strong> We never fake 4K or upscale blurry videos. You get bit-for-bit what the creator uploaded.</li><li><strong>Fast &amp; Anonymous:</strong> No login or account registration is ever required.</li><li><strong>Complete Media Support:</strong> Download Videos, Reels, Photos, Stories, and full multi-slide Carousels.</li></ul>"""
        },
        {
            "slug": "about",
            "title": "About Us",
            "main_heading": "About FastEDL",
            "subheading": "Fast Easy Download Link is an independent online media utility built for creators and social media professionals worldwide.",
            "category": "company",
            "is_system": 1,
            "seo_title": "About FastEDL - Fast Easy Download Link",
            "seo_description": "Learn about FastEDL's mission, engineering standards, privacy practices, and leadership in social media archiving.",
            "focus_keyword": "About FastEDL",
            "canonical_url": "https://fastedl.app/about",
            "og_title": "About FastEDL - Fast Easy Download Link",
            "og_description": "Learn about FastEDL's mission, engineering standards, and privacy practices.",
            "content": """<h2>Our Mission</h2><p class="lead">FastEDL was established with a singular focus: to provide a clean, ad-light, ultra-reliable tool for downloading public Instagram media in true original resolution.</p><h3>Engineering Excellence</h3><p>Unlike ad-cluttered downloaders that compress video files or fail to synchronize audio streams, FastEDL uses state-of-the-art MPEG-DASH manifest parsing and lossless FFmpeg remuxing.</p><h3>Privacy by Architecture</h3><p>We believe your browsing and archiving activities belong to you. We do not store your download history, track personal identities, or require social media logins.</p>"""
        },
        {
            "slug": "contact",
            "title": "Contact Us",
            "main_heading": "Contact FastEDL Support",
            "subheading": "Have questions, feedback, partnership inquiries, or support requests? Reach out to our dedicated team.",
            "category": "support",
            "is_system": 1,
            "seo_title": "Contact FastEDL - Customer Support & Inquiries",
            "seo_description": "Get in touch with the FastEDL team for support, feature feedback, partnership inquiries, or copyright notices.",
            "focus_keyword": "Contact FastEDL",
            "canonical_url": "https://fastedl.app/contact",
            "og_title": "Contact FastEDL - Customer Support & Inquiries",
            "og_description": "Get in touch with the FastEDL team for technical support and inquiries.",
            "content": """<h2>We're Here to Help</h2><p class="lead">Our technical support and editorial teams review all inquiries within 24 to 48 business hours.</p><h3>Support Channels</h3><ul><li><strong>General Inquiries:</strong> support@fastedl.app</li><li><strong>Partnerships &amp; Media:</strong> press@fastedl.app</li><li><strong>DMCA &amp; Copyright:</strong> dmca@fastedl.app</li></ul><p>You can also use our interactive web contact form on the Contact page for immediate database routing.</p>"""
        },
        {
            "slug": "privacy-policy",
            "title": "Privacy Policy",
            "main_heading": "FastEDL Privacy Policy",
            "subheading": "We value your privacy. Read our transparent policies regarding logs, cookies, and local caching.",
            "category": "legal",
            "is_system": 1,
            "seo_title": "FastEDL Privacy Policy - How We Protect Your Data",
            "seo_description": "Read FastEDL's complete privacy policy. Discover our zero-login architecture, cookie practices, and data retention standards.",
            "focus_keyword": "FastEDL Privacy Policy",
            "canonical_url": "https://fastedl.app/privacy-policy",
            "og_title": "FastEDL Privacy Policy",
            "og_description": "Read FastEDL's complete privacy policy and data retention standards.",
            "content": """<h2>1. Information We Do Not Collect</h2><p class="lead">FastEDL is strictly a client-initiated tool. We do not require users to create an account, register an email address, or provide personal credentials.</p><h2>2. Temporary Processing Logs</h2><p>When you submit a URL for extraction, our backend temporarily queries the source CDN to inspect format availability. Media files are streamed directly or cached transiently in memory and are deleted automatically.</p><h2>3. Cookies and Analytics</h2><p>We use minimal, privacy-conscious analytics to measure server load and bandwidth utilization. We never sell or share user data with third-party data brokers.</p>"""
        },
        {
            "slug": "terms-of-service",
            "title": "Terms of Service",
            "main_heading": "Terms of Service",
            "subheading": "Guidelines and legal conditions governing your use of FastEDL services and tools.",
            "category": "legal",
            "is_system": 1,
            "seo_title": "FastEDL Terms of Service - User Agreement",
            "seo_description": "Review the terms and conditions for using FastEDL's media extraction and creator library tools.",
            "focus_keyword": "Terms of Service",
            "canonical_url": "https://fastedl.app/terms-of-service",
            "og_title": "FastEDL Terms of Service",
            "og_description": "Review the terms and conditions for using FastEDL services.",
            "content": """<h2>1. Permitted Use</h2><p class="lead">FastEDL is provided for personal archiving, educational reference, and offline consumption of publicly accessible media.</p><h2>2. Intellectual Property Rights</h2><p>All copyright, trademark, and ownership rights in downloaded media belong entirely to the original content creators and copyright owners. Users must obtain explicit written authorization before re-distributing or monetizing any downloaded content.</p><h2>3. Prohibited Conduct</h2><p>You agree not to use FastEDL to circumvent digital rights management (DRM), scrape private user accounts, or overload platform infrastructure through automated bot attacks.</p>"""
        },
        {
            "slug": "copyright-policy",
            "title": "Copyright Policy",
            "main_heading": "Copyright & DMCA Policy",
            "subheading": "FastEDL strictly respects intellectual property rights and adheres to the Digital Millennium Copyright Act.",
            "category": "legal",
            "is_system": 1,
            "seo_title": "FastEDL DMCA & Copyright Policy - Takedown Procedures",
            "seo_description": "Learn how FastEDL complies with copyright law and the DMCA. Submit copyright inquiries or content block requests.",
            "focus_keyword": "DMCA Copyright Policy",
            "canonical_url": "https://fastedl.app/copyright-policy",
            "og_title": "FastEDL DMCA & Copyright Policy",
            "og_description": "Learn how FastEDL complies with copyright law and the DMCA.",
            "content": """<h2>DMCA Compliance Notice</h2><p class="lead">FastEDL is a content-neutral tool that accesses publicly available media directly from third-party hosting servers. FastEDL does not host, store, or index private video files.</p><h3>Filing a Takedown Notice</h3><p>If you are a copyright owner and wish to block access to specific public URLs, please email our designated agent at <strong>dmca@fastedl.app</strong> with the subject line <em>\"DMCA Takedown Notice\"</em> and include the relevant URLs and proof of ownership.</p>"""
        },
        {
            "slug": "disclaimer",
            "title": "Disclaimer",
            "main_heading": "FastEDL Disclaimer",
            "subheading": "Important notices regarding third-party trademarks, public API usage, and copyright protection.",
            "category": "legal",
            "is_system": 1,
            "seo_title": "FastEDL Legal Disclaimer & Trademark Notices",
            "seo_description": "FastEDL is an independent web tool not affiliated with or endorsed by Instagram, Meta Platforms, Inc.",
            "focus_keyword": "FastEDL Disclaimer",
            "canonical_url": "https://fastedl.app/disclaimer",
            "og_title": "FastEDL Legal Disclaimer",
            "og_description": "FastEDL is an independent web tool not affiliated with Meta Platforms, Inc.",
            "content": """<h2>Independent Utility</h2><p class="lead">FastEDL is an independent software tool and is NOT affiliated with, sponsored by, or endorsed by Instagram, Meta Platforms, Inc., or any of their subsidiary entities.</p><p>Instagram, the Instagram logo, and the Instagram camera logo are registered trademarks of Meta Platforms, Inc. All other trademarks and brand names referenced on this site belong to their respective holders.</p>"""
        },
        {
            "slug": "faq",
            "title": "FAQ",
            "main_heading": "Frequently Asked Questions",
            "subheading": "Everything you need to know about downloading Instagram videos, reels, photos, and carousels.",
            "category": "support",
            "is_system": 1,
            "seo_title": "FastEDL FAQ - Frequently Asked Questions & Answers",
            "seo_description": "Find answers to frequently asked questions about video quality, carousel downloads, audio synchronization, and supported devices.",
            "focus_keyword": "FastEDL FAQ",
            "canonical_url": "https://fastedl.app/faq",
            "og_title": "FastEDL FAQ - Frequently Asked Questions",
            "og_description": "Find answers to frequently asked questions about FastEDL video and reels downloads.",
            "content": """<h2>Frequently Asked Questions</h2><h3>Is FastEDL completely free?</h3><p>Yes. FastEDL is 100% free with unlimited downloads and zero required subscriptions.</p><h3>Where do downloaded files get saved on my device?</h3><p>On Android, Windows, and Mac, downloaded media files save directly into your system <strong>Downloads</strong> folder. On iPhone and iPad (Safari), files save to the Files app under the Downloads folder.</p><h3>Does FastEDL support downloading entire carousels?</h3><p>Yes! FastEDL detects every slide in an Instagram carousel and offers both individual slide downloads and a <strong>Download All</strong> batch button.</p>"""
        },
        {
            "slug": "how-it-works",
            "title": "How It Works",
            "main_heading": "How to Use FastEDL",
            "subheading": "A simple step-by-step tutorial on copying links and saving high-definition Instagram media.",
            "category": "guides",
            "is_system": 1,
            "seo_title": "How to Use FastEDL - Step-by-Step Instagram Download Guide",
            "seo_description": "Learn how to download Instagram reels, videos, and photos in 3 simple steps on mobile and desktop.",
            "focus_keyword": "How to Use FastEDL",
            "canonical_url": "https://fastedl.app/how-it-works",
            "og_title": "How to Use FastEDL - Step-by-Step Guide",
            "og_description": "Learn how to download Instagram reels, videos, and photos in 3 simple steps.",
            "content": """<h2>How to Download Instagram Media in 3 Steps</h2><ol><li><strong>Copy the Instagram Link:</strong> Open Instagram, locate your desired post, tap the paper airplane Share icon, and select <em>Copy Link</em>.</li><li><strong>Paste into FastEDL:</strong> Open <a href=\"https://fastedl.app\">FastEDL.app</a>, paste the link into the search bar, and tap <strong>Download</strong>.</li><li><strong>Select Quality &amp; Save:</strong> Preview the media, choose your preferred genuine resolution (e.g. 1080p Full HD), and tap <strong>Download</strong> to save it instantly.</li></ol>"""
        },
        {
            "slug": "instagram-guides",
            "title": "Instagram Guides",
            "main_heading": "Instagram Guides & Best Practices",
            "subheading": "Actionable growth playbooks, technical tutorials, and algorithm analysis for Instagram creators.",
            "category": "guides",
            "is_system": 1,
            "seo_title": "Instagram Guides & Tutorials - FastEDL Creator Academy",
            "seo_description": "Browse comprehensive Instagram guides on video formats, carousel optimization, hashtag reach, and troubleshooting.",
            "focus_keyword": "Instagram Guides",
            "canonical_url": "https://fastedl.app/instagram-guides",
            "og_title": "Instagram Guides & Tutorials - FastEDL",
            "og_description": "Browse comprehensive Instagram guides and tutorials for creators.",
            "content": """<h2>FastEDL Creator Academy</h2><p class="lead">Explore our in-depth guides covering social media algorithms, video quality benchmarks, and engagement strategies.</p><h3>Featured Guide Categories</h3><ul><li><strong>Reels Growth:</strong> Learn how adaptive streaming works and how to optimize vertical video retention.</li><li><strong>Hashtag Strategies:</strong> Master the 3-tier niche hashtag formula.</li><li><strong>Carousel Blueprints:</strong> Discover how 10-slide carousels generate 3x higher comment rates.</li></ul>"""
        }
    ]

    for p in initial_pages:
        cursor.execute("SELECT id FROM pages WHERE slug = ?", (p["slug"],))
        existing = cursor.fetchone()
        now_iso = datetime.utcnow().isoformat()
        if not existing:
            cursor.execute("""
                INSERT INTO pages (
                    slug, title, main_heading, subheading, content,
                    category, author, status, is_system, seo_title, seo_description,
                    focus_keyword, canonical_url, og_title, og_description,
                    robots, created_at, updated_at, published_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'FastEDL Editorial Team', 'published', ?, ?, ?, ?, ?, ?, ?, 'index, follow', ?, ?, ?)
            """, (
                p["slug"], p["title"], p["main_heading"], p["subheading"],
                p["content"], p["category"], p["is_system"], p["seo_title"],
                p["seo_description"], p["focus_keyword"], p["canonical_url"],
                p["og_title"], p["og_description"], now_iso, now_iso, now_iso
            ))
        else:
            cursor.execute("""
                UPDATE pages
                SET title = ?, main_heading = ?, subheading = ?, content = ?,
                    seo_title = ?, seo_description = ?, focus_keyword = ?,
                    canonical_url = ?, og_title = ?, og_description = ?, updated_at = ?
                WHERE slug = ?
            """, (
                p["title"], p["main_heading"], p["subheading"], p["content"],
                p["seo_title"], p["seo_description"], p["focus_keyword"],
                p["canonical_url"], p["og_title"], p["og_description"], now_iso,
                p["slug"]
            ))

    conn.commit()
    conn.close()
    logger.info("Database schema initialized and verified.")

if __name__ == "__main__":
    init_db()
    print("Database initialization complete.")
