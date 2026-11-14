# FastEDL - Fast Instagram Downloader & Platform Backend API

> **Download. Save. Enjoy.**  
> **FastEDL (Fast Easy Download Link)** is a production-grade FastAPI backend service powering Instagram Reels, video, photo, carousel extraction, creator tools, and an advanced Content Management System (CMS).

---

## 🚀 Backend Quickstart

### Prerequisites
- Python 3.10+
- FFmpeg (optional, recommended for HD stream merging)

### Installation & Run

```bash
# 1. Clone the repository
git clone https://github.com/VikashKhadoliya/fastedl-backend.git
cd fastedl-backend

# 2. Create virtual environment & activate
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Alternative ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/api/health`

---

## 🎨 Complete Brand Identity System

### 1. Brand Overview
- **Brand Name:** FastEDL
- **Full Name:** Fast Easy Download Link
- **Category:** Online Media Downloader
- **Primary Product:** Instagram Media Downloader
- **Tagline:** Download. Save. Enjoy.
- **Target Audience:** USA, United Kingdom, Canada, Australia, Europe, and Worldwide users.
- **Brand Personality:**
  - **Fast:** Instantaneous query resolution and direct stream delivery.
  - **Reliable:** Multi-tier extraction with Instaloader and yt-dlp fallbacks.
  - **Simple:** Clean single-input interface with clipboard paste integration.
  - **Modern:** Premium UI applying the 60-30-10 color rule with zero clutter.
  - **Professional:** Transparent policies, GDPR/CCPA alignment, and legal disclaimers.
  - **Trustworthy:** Zero password harvesting, zero cookie collection, SSRF defense.
  - **User-Friendly:** Fully accessible across mobile (iOS Safari, Android Chrome) and desktop.

### 2. Color System (60-30-10 Color Rule)
- **Primary (10% Accent/Action):** `#635BFF` (Electric Indigo) — Primary action buttons, active navigation states, brand wordmark.
- **Secondary (Structural & Depth):** `#8B5CF6` (Vibrant Violet) — Secondary accents, gradient subtle borders, icon highlights.
- **Accent (Precision Indicators):** `#06B6D4` (Cyan) — Status indicators, active indicators, format receiver accents.
- **Background (60% Dominant):** `#FFFFFF` (Pure White) — Primary page canvas.
- **Dark Background (Containers & Social):** `#0F172A` (Slate 900) — Media player background, social card backdrops.
- **Primary Text:** `#111827` (Gray 900) — High contrast, professional readability.
- **Secondary Text (30% Structural):** `#64748B` (Slate 500) — Body copy, metadata, secondary links.
- **Border:** `#E2E8F0` (Slate 200) — Crisp structural container dividing lines.

### 3. Typography
- **Primary Font:** Inter, system-ui (`font-sans`) — Modern, balanced letterforms.
- **Secondary / Technical Font:** JetBrains Mono (`font-mono`) — Technical identifiers, format tags, CDN badges.

### 4. Logo Design
The FastEDL logo features an integrated letter **F** combined with a precision **downward download arrow**:
- Top arm of the "F" extends horizontally with crisp geometry.
- Middle crossbar seamlessly bends into a downward-pointing arrow.
- Cyan accent receiver bar at the base (`#06B6D4`).
- Wordmark: **Fast** in `#111827` + **EDL** in `#635BFF` with an accent dot in `#06B6D4`.

---

## 📱 Social Media Branding System

### Instagram Profile (@fastedl)
- **Avatar:** Minimal geometric squircle (`#635BFF`) with white integrated F-Arrow glyph (`1080x1080px`).
- **Bio:**
  ```text
  FastEDL • Fast Easy Download Link
  Download. Save. Enjoy.
  ⚡ Simple, fast & mobile-friendly Instagram media access.
  🔒 Zero credentials required.
  🔗 fastedl.app
  ```

### Facebook Page (FastEDL)
- **Profile Picture:** Square FastEDL brand emblem (`#635BFF` with white glyph).
- **Cover Banner (820x312px):** Dark `#0F172A` background with electric indigo ambient glow, full wordmark, tagline "Download. Save. Enjoy.", and key trust messaging: "Simple to use • Mobile friendly • Secure URL handling".

### YouTube Channel (@FastEDL)
- **Profile Avatar:** 800x800px FastEDL high-contrast icon.
- **Channel Banner (2560x1440px):** Minimal dark grid layout displaying the FastEDL logo, tagline "Download. Save. Enjoy.", and clean device mockups showing iPhone and desktop usage.

### Open Graph / Social Sharing Card
- **Resolution:** 1200x630px vector SVG (`public/og-image.svg`).
- **Elements:** Slate 900 background (`#0F172A`), large FastEDL emblem, "Fast Easy Download Link" classification, and trust pills.

---

## 🚀 Core Features

- **Instagram Reel Downloader:** Save public reels in full 1080p MP4 format with synchronized audio.
- **Instagram Video & IGTV Saver:** Access standard feed videos and long-form clips in original clarity.
- **Single Photo Downloader:** Extract original uncompressed JPEG images from public posts.
- **Carousel Post Support:** Multi-slide album extraction with thumbnail slider, individual slide downloads, and "Download All" capability.
- **Media Preview:** In-browser video player, responsive image preview, creator avatar/handle, like counts, and caption toggle.
- **Direct Stream Download:** Safe chunk-streaming proxy (`/api/download`) forcing browser attachment downloads while mitigating CORS/hotlinking restrictions.
- **SSRF & Security Defense:** Strict domain allowlisting (`*.cdninstagram.com`, `*.fbcdn.net`, `instagram.com`), DNS resolution validation against private IP ranges, 250MB size limit, and socket timeouts.

---

## 📂 Project Architecture

```
instagram-downloader/
├── main.py                     # Root FastAPI entrypoint (delegates to backend.main)
├── README.md                   # Complete brand system & setup guide
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application, CORS, exception handlers
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # FastEDL settings, limits, timeouts
│   │   └── security.py         # URL regex, SSRF prevention, safe filenames
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extractor.py        # Multi-strategy extractor (Instaloader + yt-dlp)
│   │   └── downloader.py       # Safe chunk-streaming proxy
│   └── routes/
│       ├── __init__.py
│       └── api.py              # API endpoints (/validate, /fetch, /download, /health)
└── frontend/
    ├── package.json
    ├── next.config.mjs
    ├── public/
    │   ├── icon.svg            # FastEDL app icon
    │   ├── favicon.svg         # Vector favicon
    │   └── og-image.svg        # 1200x630 Open Graph brand preview
    ├── src/
    │   ├── app/
    │   │   ├── icon.svg        # Next.js automatic vector favicon
    │   │   ├── layout.js       # Root layout with FastEDL SEO metadata
    │   │   ├── globals.css     # CSS design tokens (60-30-10 palette)
    │   │   ├── page.js         # Home page (Hero, Form, Features, Steps, FAQ)
    │   │   ├── how-to-use/     # Device walkthroughs (iPhone, Android, PC/Mac)
    │   │   ├── about/          # About FastEDL & principles
    │   │   ├── contact/        # Contact & DMCA support form
    │   │   ├── privacy-policy/ # Privacy policy (no credential collection)
    │   │   ├── terms-of-service/# Terms of service and fair use
    │   │   ├── disclaimer/     # Non-affiliation disclaimer
    │   │   ├── sitemap.js      # Dynamic XML sitemap
    │   │   └── robots.js       # Robots.txt generator
    │   ├── components/
    │   │   ├── FastEDLLogo.jsx # Reusable FastEDL logo (icon & wordmark)
    │   │   ├── Navbar.jsx      # Header with logo & tagline
    │   │   ├── Footer.jsx      # Footer with brand links & disclaimer
    │   │   ├── DownloaderForm.jsx # Input field, paste button, tabs, progress
    │   │   ├── MediaPreview.jsx# Carousel slider, video player, download buttons
    │   │   ├── FeaturesSection.jsx
    │   │   ├── HowToUseSteps.jsx
    │   │   └── FAQSection.jsx
    │   └── lib/
    │       └── api.js          # API client
```

---

## ⚡ Windows PowerShell Setup Instructions

### Prerequisites
- Windows 10/11
- Python 3.10+ (installed and in PATH)
- Node.js 18+ and npm (installed and in PATH)

---

### Step 1: Start the FastEDL Backend

Open a PowerShell terminal in the project root:

```powershell
# 1. Navigate to project root
cd C:\Users\rahul\instagram-downloader

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Ensure required Python dependencies are installed
pip install fastapi uvicorn requests instaloader yt-dlp pydantic

# 4. Start the FastEDL FastAPI backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be available at:
- **Base URL:** `http://127.0.0.1:8000`
- **Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **Health Check:** `http://127.0.0.1:8000/api/health`

---

### Step 2: Start the FastEDL Frontend

Open a second PowerShell terminal:

```powershell
# 1. Navigate to frontend directory
cd C:\Users\rahul\instagram-downloader\frontend

# 2. Install dependencies (if needed)
npm install

# 3. Start Next.js development server
npm run dev
```

Open your browser to:
👉 **`http://localhost:3000`**

To produce an optimized production build:
```powershell
cd C:\Users\rahul\instagram-downloader\frontend
npm run build
npm run start
```

---

## 🔒 Platform Limitations & Fair Use Compliance

1. **Public Accounts Only:** FastEDL only processes content from public Instagram profiles. Posts from private accounts cannot and will not be retrieved.
2. **Zero Password Collection:** FastEDL never asks for, logs, or stores Instagram passwords, session tokens, or cookies.
3. **Instagram Rate Limits:** Instagram may occasionally rate-limit requests during peak periods. The multi-tier engine utilizes Instaloader and yt-dlp fallbacks to maintain resilience.
4. **Fair Use & Copyright:** All content accessed through FastEDL must comply with Fair Use (17 U.S. Code § 107) for lawful personal archival, research, and non-commercial reference. Users are solely responsible for respecting creator copyrights.
