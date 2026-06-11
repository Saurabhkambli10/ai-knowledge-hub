# AI Knowledge Hub — Deployment Guide

## What you'll have when done
A live web app at a URL like `https://your-name-ai-knowledge-hub.streamlit.app`
that you can open from any browser, on any device, for **free**.

---

## Step 1 — Get a free Gemini API key (5 minutes)

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your **personal** Google account (not work email)
3. Click **"Create API key"**
4. Copy the key (looks like `AIzaSy...`) — save it somewhere safe

> The free tier gives you 15 requests/minute and 1 million tokens/day.
> More than enough for personal use.

---

## Step 2 — Put the code on GitHub (10 minutes)

You need a free GitHub account to host the code.

### If you don't have GitHub yet:
1. Go to **https://github.com** → Sign up (use your personal email)

### Create a new repository:
1. Click the **"+"** icon (top right) → **New repository**
2. Name it: `ai-knowledge-hub`
3. Set it to **Public** (required for free Streamlit hosting)
4. Click **"Create repository"**

### Upload the files:
1. On your new repository page, click **"uploading an existing file"**
2. Drag and drop ALL files from the `ai-knowledge-hub` folder you received:
   ```
   app.py
   requirements.txt
   .gitignore
   utils/
     __init__.py
     ai_utils.py
     youtube_utils.py
     doc_utils.py
   .streamlit/
     config.toml
     secrets.toml.example
   DEPLOYMENT_GUIDE.md
   ```
3. Click **"Commit changes"**

> **Important:** Do NOT upload `.streamlit/secrets.toml` (it contains your API key).
> The `.gitignore` file prevents this from happening accidentally.

---

## Step 3 — Deploy on Streamlit Cloud (5 minutes)

1. Go to **https://share.streamlit.io**
2. Sign in with your **personal** GitHub account
3. Click **"New app"**
4. Fill in:
   - **Repository:** `your-github-username/ai-knowledge-hub`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Advanced settings"** → **Secrets** section
6. Paste this (replacing with your actual key):
   ```toml
   GEMINI_API_KEY = "AIzaSy...your-key-here..."
   ```
7. Click **"Deploy!"**

Wait ~2 minutes for the first build to complete.

🎉 **Your app is now live** at a URL like:
`https://your-username-ai-knowledge-hub-app-xxxx.streamlit.app`

---

## Step 4 — Using your app

### Analyse a YouTube video:
1. Click **📹 YouTube Analysis** in the sidebar
2. Paste any YouTube URL
3. Click **"Analyse Video"**
4. Results appear in ~15–30 seconds

### Upload a document:
1. Click **📄 Document Upload**
2. Drop your PDF, Word doc, or other file
3. Click **"Analyse Document"**

### Compare multiple items:
1. Add at least 2 items to your knowledge base first
2. Click **⚖️ Compare & Analyse**
3. Select the items to compare
4. Click **"Compare"**

### Save your knowledge base:
- Click **💾 Save / Load Data** in the sidebar
- Download as JSON to keep your data permanently
- Re-upload it next session to restore everything

---

## Architecture Overview

```
User's Browser
      │
      ▼
Streamlit Cloud (Free hosting)
  app.py  ──► utils/youtube_utils.py  ──► YouTube Transcript API (free, no key)
         ──► utils/doc_utils.py       ──► PyMuPDF / python-docx / python-pptx
         ──► utils/ai_utils.py        ──► Gemini 1.5 Flash API (free tier)
```

**Technology choices — all free:**

| Component | Technology | Why |
|-----------|-----------|-----|
| Web UI | Streamlit | No-code UI, free hosting |
| AI engine | Gemini 1.5 Flash | Best free-tier AI, 1M tokens/day |
| YouTube | youtube-transcript-api | No API key needed |
| PDF | PyMuPDF | Fast, reliable, free |
| Word docs | python-docx | Official, free |
| Charts | Plotly | Interactive, free |
| Data storage | JSON export (browser) | No database needed |

---

## Ownership & Portability

Everything is tied to your **personal** accounts:
- **GitHub** (personal) — owns the code
- **Google** (personal) — owns the Gemini API key
- **Streamlit** (signed in via personal GitHub) — owns the deployment

When you leave your work account, nothing breaks.

### Migrating from work tools:
- Export your knowledge base as JSON from the app (💾 sidebar)
- Re-import it after moving to your personal account
- Update the Gemini API key in Streamlit Cloud settings

---

## Updating the app

1. Edit any file in your GitHub repository
2. Streamlit Cloud auto-redeploys within ~1 minute

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "API key not found" | Check Streamlit Cloud secrets — key name must be `GEMINI_API_KEY` |
| "No transcript found" | The video has captions disabled; try a different video |
| "Module not found" | Check that `requirements.txt` was uploaded to GitHub |
| App is slow | Gemini free tier has rate limits; wait 60s and retry |
| Lost my data | Always export JSON before closing the browser tab |

---

## Free tier limits (as of 2024)

| Service | Free limit |
|---------|-----------|
| Streamlit Cloud | 1 app, always-on |
| Gemini 1.5 Flash | 15 RPM, 1M tokens/day |
| YouTube Transcript | Unlimited |

For personal use, these limits are generous. You would need to analyze hundreds of videos per day to hit them.
