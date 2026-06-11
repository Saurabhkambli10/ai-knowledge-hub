"""
AI Knowledge & Analytics Hub
A Streamlit web application for analyzing YouTube videos and documents.

Powered by: Google Gemini (free tier) via Google AI Studio
Hosting:    Streamlit Community Cloud (free)
"""

import json
import uuid
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from utils.ai_utils import analyze_content, compare_items, semantic_search
from utils.youtube_utils import extract_video_id, get_transcript, get_video_metadata
from utils.doc_utils import extract_text_from_file, get_file_icon

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Knowledge Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px; padding: 20px; color: white; margin: 8px 0;
    }
    .insight-card {
        background: #f8f9ff; border-left: 4px solid #667eea;
        border-radius: 6px; padding: 12px 16px; margin: 6px 0;
    }
    .action-card {
        background: #f0fff4; border-left: 4px solid #38a169;
        border-radius: 6px; padding: 12px 16px; margin: 6px 0;
    }
    .quote-card {
        background: #fffbeb; border-left: 4px solid #d69e2e;
        border-radius: 6px; padding: 12px 16px; margin: 6px 0;
        font-style: italic;
    }
    .tag-pill {
        display: inline-block; background: #ebf4ff; color: #3b82f6;
        border-radius: 20px; padding: 2px 10px; margin: 3px; font-size: 0.8rem;
    }
    .sentiment-positive { color: #38a169; font-weight: bold; }
    .sentiment-negative { color: #e53e3e; font-weight: bold; }
    .sentiment-neutral  { color: #718096; font-weight: bold; }
    .sentiment-mixed    { color: #d69e2e; font-weight: bold; }
    div[data-testid="stSidebarContent"] { background-color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)

# ── Session state initialisation ──────────────────────────────────────────────

def init_state():
    if "items" not in st.session_state:
        st.session_state.items = []          # List of analyzed content items
    if "api_key" not in st.session_state:
        # Check Streamlit secrets first, then fall back to empty
        try:
            st.session_state.api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            st.session_state.api_key = ""
    if "page" not in st.session_state:
        st.session_state.page = "Dashboard"

init_state()

# ── Helpers ───────────────────────────────────────────────────────────────────

def sentiment_badge(sentiment: str) -> str:
    icons = {"positive": "😊", "negative": "😟", "neutral": "😐", "mixed": "🤔"}
    return icons.get(sentiment, "❓") + " " + sentiment.capitalize()

def difficulty_badge(level: str) -> str:
    icons = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}
    return icons.get(level, "⚪") + " " + level.capitalize()

def render_tags(tags: list) -> str:
    return " ".join(f'<span class="tag-pill">{t}</span>' for t in tags)

def get_item_by_id(item_id: str) -> dict | None:
    for item in st.session_state.items:
        if item["id"] == item_id:
            return item
    return None

def delete_item(item_id: str):
    st.session_state.items = [i for i in st.session_state.items if i["id"] != item_id]

def export_knowledge_base() -> str:
    return json.dumps(st.session_state.items, indent=2, ensure_ascii=False)

def import_knowledge_base(json_str: str):
    data = json.loads(json_str)
    if isinstance(data, list):
        # Merge: avoid duplicates by ID
        existing_ids = {i["id"] for i in st.session_state.items}
        for item in data:
            if item.get("id") not in existing_ids:
                st.session_state.items.append(item)
        return len(data)
    raise ValueError("Invalid knowledge base format.")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://em-content.zobj.net/source/apple/391/brain_1f9e0.png", width=60)
    st.title("AI Knowledge Hub")
    st.caption("Powered by Gemini · Built with Streamlit")
    st.divider()

    # Navigation
    pages = {
        "Dashboard":          "🏠",
        "YouTube Analysis":   "📹",
        "Document Upload":    "📄",
        "Knowledge Base":     "🗄️",
        "Compare & Analyse":  "⚖️",
    }
    for page_name, icon in pages.items():
        if st.button(f"{icon} {page_name}", use_container_width=True,
                     type="primary" if st.session_state.page == page_name else "secondary"):
            st.session_state.page = page_name
            st.rerun()

    st.divider()

    # API Key config
    with st.expander("⚙️ API Settings"):
        api_input = st.text_input(
            "Gemini API Key",
            value=st.session_state.api_key,
            type="password",
            help="Get a free key at https://aistudio.google.com/app/apikey"
        )
        if api_input != st.session_state.api_key:
            st.session_state.api_key = api_input
            st.success("Key saved!")

        st.caption("[Get free API key →](https://aistudio.google.com/app/apikey)")

    # Knowledge base export/import
    with st.expander("💾 Save / Load Data"):
        if st.session_state.items:
            st.download_button(
                "⬇️ Export Knowledge Base",
                data=export_knowledge_base(),
                file_name=f"knowledge_base_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
        uploaded_kb = st.file_uploader("⬆️ Import Knowledge Base", type=["json"], key="kb_import")
        if uploaded_kb:
            try:
                count = import_knowledge_base(uploaded_kb.read().decode())
                st.success(f"Imported {count} items!")
                st.rerun()
            except Exception as e:
                st.error(f"Import failed: {e}")

    st.divider()
    st.caption(f"📚 {len(st.session_state.items)} items in knowledge base")

# ── API key guard ─────────────────────────────────────────────────────────────

def require_api_key():
    if not st.session_state.api_key:
        st.warning(
            "⚠️ **Gemini API key required.** "
            "Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey) "
            "and paste it in **⚙️ API Settings** in the sidebar.",
            icon="🔑"
        )
        st.stop()

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

def page_dashboard():
    st.title("🏠 Dashboard")

    items = st.session_state.items
    if not items:
        st.info(
            "👋 **Welcome to AI Knowledge Hub!**\n\n"
            "Start by:\n"
            "1. Setting your Gemini API key in ⚙️ API Settings (sidebar)\n"
            "2. Adding a YouTube video via **📹 YouTube Analysis**\n"
            "3. Uploading a document via **📄 Document Upload**",
        )
        return

    # ── Top metrics ───────────────────────────────────────────────────────────
    total = len(items)
    yt_count = sum(1 for i in items if i["type"] == "youtube")
    doc_count = total - yt_count
    all_tags = [tag for i in items for tag in i.get("analysis", {}).get("tags", [])]
    unique_tags = len(set(all_tags))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📚 Total Items", total)
    c2.metric("📹 YouTube Videos", yt_count)
    c3.metric("📄 Documents", doc_count)
    c4.metric("🏷️ Unique Tags", unique_tags)

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        # ── Topics frequency bar chart ─────────────────────────────────────
        all_topics = []
        for item in items:
            for t in item.get("analysis", {}).get("topics", []):
                all_topics.append({"topic": t["name"], "relevance": t["relevance"]})

        if all_topics:
            df_topics = pd.DataFrame(all_topics)
            df_agg = df_topics.groupby("topic")["relevance"].mean().reset_index()
            df_agg = df_agg.sort_values("relevance", ascending=False).head(12)
            fig = px.bar(
                df_agg, x="relevance", y="topic", orientation="h",
                title="🗂️ Top Topics Across Knowledge Base",
                color="relevance", color_continuous_scale="Viridis",
                labels={"relevance": "Avg Relevance", "topic": "Topic"},
            )
            fig.update_layout(height=380, showlegend=False, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # ── Sentiment distribution ─────────────────────────────────────────
        sentiments = [i.get("analysis", {}).get("sentiment", "neutral") for i in items]
        df_sent = pd.Series(sentiments).value_counts().reset_index()
        df_sent.columns = ["Sentiment", "Count"]
        color_map = {"positive": "#38a169", "negative": "#e53e3e", "neutral": "#718096", "mixed": "#d69e2e"}
        fig2 = px.pie(
            df_sent, names="Sentiment", values="Count",
            title="😊 Sentiment Distribution",
            color="Sentiment", color_discrete_map=color_map,
            hole=0.4,
        )
        fig2.update_layout(height=280)
        st.plotly_chart(fig2, use_container_width=True)

        # ── Content type breakdown ─────────────────────────────────────────
        ctypes = [i.get("analysis", {}).get("content_type", "other") for i in items]
        df_ct = pd.Series(ctypes).value_counts().reset_index()
        df_ct.columns = ["Type", "Count"]
        fig3 = px.bar(df_ct, x="Type", y="Count", title="📋 Content Types",
                      color="Count", color_continuous_scale="Blues")
        fig3.update_layout(height=240, showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    # ── Recent items ──────────────────────────────────────────────────────────
    st.subheader("🕐 Recent Items")
    for item in reversed(items[-6:]):
        analysis = item.get("analysis", {})
        with st.expander(
            f"{'📹' if item['type'] == 'youtube' else get_file_icon(item.get('file_type',''))} "
            f"{analysis.get('title', item.get('title', 'Untitled'))} "
            f"· {item.get('date_added', '')[:10]}"
        ):
            st.write(analysis.get("top_takeaway", analysis.get("executive_summary", "")[:300]))
            tags = analysis.get("tags", [])
            if tags:
                st.markdown(render_tags(tags[:8]), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: YOUTUBE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

def page_youtube():
    st.title("📹 YouTube Analysis")
    require_api_key()

    st.markdown(
        "Paste a YouTube URL and get an AI-powered summary, key insights, action items, "
        "topic breakdown, and more — instantly."
    )

    url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        help="Supports youtube.com and youtu.be links"
    )

    analyze_btn = st.button("🚀 Analyse Video", type="primary", disabled=not url.strip())

    if analyze_btn and url.strip():
        video_id = extract_video_id(url.strip())
        if not video_id:
            st.error("❌ Could not parse a valid YouTube video ID from this URL.")
            return

        metadata = get_video_metadata(url.strip())

        with st.status("Analysing video...", expanded=True) as status:
            st.write("📥 Fetching transcript...")
            try:
                transcript, lang = get_transcript(video_id)
            except ValueError as e:
                st.error(str(e))
                return

            st.write(f"✅ Transcript fetched ({len(transcript.split()):,} words, language: {lang})")
            st.write("🤖 Sending to Gemini for analysis...")

            try:
                analysis = analyze_content(transcript, st.session_state.api_key)
            except Exception as e:
                st.error(f"Gemini analysis failed: {e}")
                return

            st.write("✅ Analysis complete!")
            status.update(label="Analysis complete!", state="complete")

        # Save to knowledge base
        item = {
            "id": str(uuid.uuid4()),
            "type": "youtube",
            "title": analysis.get("title", f"Video {video_id}"),
            "url": metadata["url"],
            "video_id": video_id,
            "thumbnail": metadata.get("thumbnail", ""),
            "date_added": datetime.now().isoformat(),
            "raw_text": transcript[:5000],   # Store first 5K chars for search
            "analysis": analysis,
            "language": lang,
        }
        st.session_state.items.append(item)
        st.success(f"✅ Saved to Knowledge Base: **{analysis.get('title', 'Video')}**")

        _render_analysis(analysis, metadata)


def _render_analysis(analysis: dict, metadata: dict = None):
    """Render a full analysis result."""

    st.divider()

    # ── Header ────────────────────────────────────────────────────────────────
    title = analysis.get("title", "Analysis")
    st.subheader(f"📊 {title}")

    meta_cols = st.columns(4)
    meta_cols[0].markdown(f"**Sentiment:** {sentiment_badge(analysis.get('sentiment','neutral'))}")
    meta_cols[1].markdown(f"**Level:** {difficulty_badge(analysis.get('difficulty_level','beginner'))}")
    meta_cols[2].markdown(f"**Type:** 📋 {analysis.get('content_type','—').capitalize()}")
    meta_cols[3].markdown(f"**~Words:** {analysis.get('word_count_estimate', 0):,}")

    # ── Thumbnail (YouTube only) ──────────────────────────────────────────────
    if metadata and metadata.get("thumbnail"):
        st.image(metadata["thumbnail"], use_container_width=False, width=360)

    # ── Top takeaway ─────────────────────────────────────────────────────────
    if analysis.get("top_takeaway"):
        st.info(f"💡 **Top Takeaway:** {analysis['top_takeaway']}")

    # ── Tabs for detailed view ────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 Summary", "🔑 Key Insights", "✅ Action Items", "💬 Quotes", "📊 Topics"
    ])

    with tab1:
        st.markdown(analysis.get("executive_summary", "No summary available."))
        if analysis.get("key_statistics"):
            st.markdown("**Key Statistics / Data Points:**")
            for stat in analysis["key_statistics"]:
                st.markdown(f"- {stat}")

    with tab2:
        for insight in analysis.get("key_insights", []):
            st.markdown(f'<div class="insight-card">💡 {insight}</div>', unsafe_allow_html=True)

    with tab3:
        for action in analysis.get("action_items", []):
            st.markdown(f'<div class="action-card">✅ {action}</div>', unsafe_allow_html=True)

    with tab4:
        for quote in analysis.get("important_quotes", []):
            st.markdown(f'<div class="quote-card">❝ {quote} ❞</div>', unsafe_allow_html=True)

    with tab5:
        topics = analysis.get("topics", [])
        if topics:
            df = pd.DataFrame(topics)
            fig = px.bar(
                df.sort_values("relevance", ascending=True),
                x="relevance", y="name", orientation="h",
                color="relevance", color_continuous_scale="Viridis",
                title="Topic Relevance Breakdown",
                labels={"relevance": "Relevance %", "name": "Topic"},
            )
            fig.update_layout(height=max(250, len(topics) * 45), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            for t in topics:
                st.markdown(f"**{t['name']}** ({t['relevance']}%) — {t.get('description', '')}")

    # ── Tags ──────────────────────────────────────────────────────────────────
    tags = analysis.get("tags", [])
    if tags:
        st.markdown("**🏷️ Tags:**")
        st.markdown(render_tags(tags), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: DOCUMENT UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def page_documents():
    st.title("📄 Document Upload")
    require_api_key()

    st.markdown(
        "Upload a document and get instant AI analysis: summary, key insights, action items, and more."
    )
    st.caption("Supported: PDF, Word (.docx), PowerPoint (.pptx), Excel (.xlsx), Text (.txt/.md), CSV")

    uploaded = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "pptx", "xlsx", "xls", "txt", "md", "csv"],
        help="Max 200 MB",
    )

    if uploaded:
        st.info(f"📎 **{uploaded.name}** ({uploaded.size / 1024:.1f} KB)")

        if st.button("🚀 Analyse Document", type="primary"):
            with st.status("Analysing document...", expanded=True) as status:
                st.write("📥 Extracting text...")
                try:
                    text, file_type = extract_text_from_file(uploaded)
                except (ValueError, ImportError) as e:
                    st.error(str(e))
                    return

                word_count = len(text.split())
                st.write(f"✅ Extracted {word_count:,} words from {file_type}")
                st.write("🤖 Sending to Gemini for analysis...")

                try:
                    analysis = analyze_content(text, st.session_state.api_key)
                except Exception as e:
                    st.error(f"Gemini analysis failed: {e}")
                    return

                st.write("✅ Analysis complete!")
                status.update(label="Analysis complete!", state="complete")

            item = {
                "id": str(uuid.uuid4()),
                "type": "document",
                "file_type": file_type,
                "title": analysis.get("title", uploaded.name),
                "filename": uploaded.name,
                "date_added": datetime.now().isoformat(),
                "raw_text": text[:5000],
                "analysis": analysis,
            }
            st.session_state.items.append(item)
            st.success(f"✅ Saved to Knowledge Base: **{analysis.get('title', uploaded.name)}**")

            _render_analysis(analysis)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════

def page_knowledge_base():
    st.title("🗄️ Knowledge Base")

    items = st.session_state.items
    if not items:
        st.info("Your knowledge base is empty. Add videos or documents to get started.")
        return

    # ── Search ────────────────────────────────────────────────────────────────
    col_search, col_filter = st.columns([3, 1])
    with col_search:
        query = st.text_input("🔍 Search", placeholder="Search by topic, keyword, or question...")
    with col_filter:
        filter_type = st.selectbox("Filter", ["All", "YouTube", "Documents"])

    # Apply type filter
    filtered = items
    if filter_type == "YouTube":
        filtered = [i for i in items if i["type"] == "youtube"]
    elif filter_type == "Documents":
        filtered = [i for i in items if i["type"] == "document"]

    # Apply semantic search
    if query.strip() and st.session_state.api_key:
        with st.spinner("Searching..."):
            try:
                relevant_ids = semantic_search(
                    query, [
                        {
                            "id": i["id"],
                            "title": i.get("analysis", {}).get("title", ""),
                            "executive_summary": i.get("analysis", {}).get("executive_summary", ""),
                            "tags": i.get("analysis", {}).get("tags", []),
                        }
                        for i in filtered
                    ],
                    st.session_state.api_key
                )
                filtered = [i for i in filtered if i["id"] in relevant_ids]
                st.caption(f"Found {len(filtered)} relevant items for: *{query}*")
            except Exception as e:
                st.warning(f"Search error: {e}")
    elif query.strip():
        # Fallback: simple text match
        q = query.lower()
        filtered = [
            i for i in filtered
            if q in json.dumps(i.get("analysis", {})).lower()
            or q in i.get("raw_text", "").lower()
        ]

    st.caption(f"Showing {len(filtered)} of {len(items)} items")
    st.divider()

    # ── Item cards ────────────────────────────────────────────────────────────
    for item in reversed(filtered):
        analysis = item.get("analysis", {})
        title = analysis.get("title", item.get("title", "Untitled"))
        icon = "📹" if item["type"] == "youtube" else get_file_icon(item.get("file_type", ""))
        date_str = item.get("date_added", "")[:10]

        with st.expander(f"{icon} **{title}** · {date_str}"):
            col1, col2 = st.columns([4, 1])

            with col1:
                # Summary
                summary = analysis.get("executive_summary", "")
                st.markdown(summary[:600] + ("..." if len(summary) > 600 else ""))

                # Meta row
                badges = []
                if analysis.get("sentiment"):
                    badges.append(sentiment_badge(analysis["sentiment"]))
                if analysis.get("difficulty_level"):
                    badges.append(difficulty_badge(analysis["difficulty_level"]))
                if analysis.get("content_type"):
                    badges.append(f"📋 {analysis['content_type'].capitalize()}")
                st.markdown("  ·  ".join(badges))

                # Tags
                tags = analysis.get("tags", [])
                if tags:
                    st.markdown(render_tags(tags[:8]), unsafe_allow_html=True)

            with col2:
                if item["type"] == "youtube" and item.get("thumbnail"):
                    st.image(item["thumbnail"], width=140)
                if item["type"] == "youtube":
                    st.markdown(f"[▶ Watch]({item['url']})")
                if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                    delete_item(item["id"])
                    st.rerun()

            # Full analysis in nested tabs
            if analysis:
                t1, t2, t3 = st.tabs(["🔑 Insights", "✅ Actions", "📊 Topics"])
                with t1:
                    for ins in analysis.get("key_insights", [])[:5]:
                        st.markdown(f"• {ins}")
                with t2:
                    for act in analysis.get("action_items", [])[:5]:
                        st.markdown(f"• {act}")
                with t3:
                    topics = analysis.get("topics", [])
                    if topics:
                        df = pd.DataFrame(topics)[["name", "relevance"]]
                        df.columns = ["Topic", "Relevance"]
                        st.dataframe(df, hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE: COMPARE & ANALYSE
# ═══════════════════════════════════════════════════════════════════════════════

def page_compare():
    st.title("⚖️ Compare & Analyse")
    require_api_key()

    items = st.session_state.items
    if len(items) < 2:
        st.info(
            "You need at least **2 items** in your knowledge base to compare. "
            "Add more videos or documents first."
        )
        return

    st.markdown(
        "Select 2 or more items to compare. The AI will find common themes, "
        "contradictions, trends, and consolidated recommendations."
    )

    # ── Item selection ────────────────────────────────────────────────────────
    item_options = {
        i["id"]: f"{'📹' if i['type']=='youtube' else '📄'} {i.get('analysis',{}).get('title', i.get('title','Untitled'))}"
        for i in items
    }
    selected_ids = st.multiselect(
        "Select items to compare",
        options=list(item_options.keys()),
        format_func=lambda x: item_options[x],
        default=list(item_options.keys())[:min(3, len(items))],
        help="Select 2–6 items for best results"
    )

    if len(selected_ids) < 2:
        st.warning("Please select at least 2 items.")
        return

    compare_btn = st.button(
        f"🚀 Compare {len(selected_ids)} Items",
        type="primary"
    )

    if compare_btn:
        selected_items = [get_item_by_id(sid) for sid in selected_ids if get_item_by_id(sid)]
        payloads = [
            {
                "id": it["id"],
                "title": it.get("analysis", {}).get("title", "Untitled"),
                "executive_summary": it.get("analysis", {}).get("executive_summary", ""),
                "key_insights": it.get("analysis", {}).get("key_insights", []),
                "topics": it.get("analysis", {}).get("topics", []),
            }
            for it in selected_items
        ]

        with st.spinner("🤖 Running comparative analysis..."):
            try:
                comparison = compare_items(payloads, st.session_state.api_key)
            except Exception as e:
                st.error(f"Comparison failed: {e}")
                return

        st.success("✅ Comparison complete!")
        st.divider()

        # ── Render comparison ─────────────────────────────────────────────────
        st.subheader(f"🌐 {comparison.get('overall_theme', 'Comparison Results')}")

        meta_c1, meta_c2 = st.columns(2)
        meta_c1.metric("Overall Sentiment", comparison.get("overall_sentiment", "—").capitalize())
        meta_c2.metric("Consensus Level", comparison.get("consensus_level", "—").capitalize())

        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🤝 Common Themes", "⚡ Agreements & Contradictions",
            "🎯 Unique Insights", "📈 Trends & Gaps", "✅ Recommendations"
        ])

        with tab1:
            themes = comparison.get("common_themes", [])
            if themes:
                for t in themes:
                    st.markdown(f'<div class="insight-card">🔗 {t}</div>', unsafe_allow_html=True)
            st.markdown("**Trend Analysis:**")
            st.write(comparison.get("trend_analysis", ""))

        with tab2:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("### ✅ Agreements")
                for a in comparison.get("key_agreements", []):
                    st.markdown(f'<div class="action-card">✓ {a}</div>', unsafe_allow_html=True)
            with col_b:
                st.markdown("### ⚠️ Contradictions")
                for c in comparison.get("key_contradictions", []):
                    st.markdown(f'<div class="quote-card">⚡ {c}</div>', unsafe_allow_html=True)

        with tab3:
            for entry in comparison.get("unique_insights_per_item", []):
                st.markdown(f"**{entry.get('title', 'Item')}**")
                for ins in entry.get("unique_insights", []):
                    st.markdown(f"  • {ins}")

        with tab4:
            col_t, col_g = st.columns(2)
            with col_t:
                st.markdown("### 📈 Trends")
                st.write(comparison.get("trend_analysis", ""))
            with col_g:
                st.markdown("### 🕳️ Knowledge Gaps")
                for gap in comparison.get("knowledge_gaps", []):
                    st.markdown(f"  • {gap}")

        with tab5:
            for rec in comparison.get("recommendations", []):
                st.markdown(f'<div class="action-card">🎯 {rec}</div>', unsafe_allow_html=True)
            st.markdown("**Consolidated Action Items:**")
            for act in comparison.get("consolidated_action_items", []):
                st.markdown(f"  • {act}")

        # ── Topic overlap chart ───────────────────────────────────────────────
        st.divider()
        st.subheader("📊 Topic Coverage Across Selected Items")
        topic_matrix = {}
        for it in selected_items:
            title = it.get("analysis", {}).get("title", "Untitled")[:30]
            for t in it.get("analysis", {}).get("topics", []):
                if t["name"] not in topic_matrix:
                    topic_matrix[t["name"]] = {}
                topic_matrix[t["name"]][title] = t["relevance"]

        if topic_matrix:
            df_matrix = pd.DataFrame(topic_matrix).T.fillna(0)
            fig = px.imshow(
                df_matrix,
                title="Topic Relevance Heatmap",
                color_continuous_scale="Viridis",
                labels={"color": "Relevance"},
                aspect="auto",
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

page = st.session_state.page
if page == "Dashboard":
    page_dashboard()
elif page == "YouTube Analysis":
    page_youtube()
elif page == "Document Upload":
    page_documents()
elif page == "Knowledge Base":
    page_knowledge_base()
elif page == "Compare & Analyse":
    page_compare()
