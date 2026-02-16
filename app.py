import streamlit as st
import requests
import re
import time
import os
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="YouTube Tools",
    page_icon="🎬",
    layout="wide"
)

# API endpoint (use environment variable or default to localhost)
API_URL = os.environ.get("API_URL", "http://localhost:8080")


def get_download_progress(video_id):
    """Get download progress from API"""
    try:
        response = requests.get(
            f"{API_URL}/api/progress/{video_id}",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None


def format_bytes(bytes_val):
    """Format bytes to human readable string"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    else:
        return f"{bytes_val / (1024 * 1024):.1f} MB"


def format_speed(speed):
    """Format download speed"""
    if speed < 1024:
        return f"{speed:.0f} B/s"
    elif speed < 1024 * 1024:
        return f"{speed / 1024:.1f} KB/s"
    else:
        return f"{speed / (1024 * 1024):.1f} MB/s"

def extract_audio_info(video_url):
    """Extract audio information from video URL"""
    try:
        response = requests.post(
            f"{API_URL}/api/audio",
            json={"url": video_url},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {"error": error_data.get("error", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def get_video_info(video_url):
    """Get video metadata"""
    try:
        response = requests.post(
            f"{API_URL}/api/info",
            json={"url": video_url},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {"error": error_data.get("error", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If already a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None

def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    if not seconds:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def thumbnail_tab():
    """Thumbnail extraction tab"""
    st.header("📸 YouTube Thumbnail Downloader")
    st.markdown("Download high-quality thumbnails from any YouTube video")

    col1, col2 = st.columns([3, 1])

    with col1:
        thumb_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL",
            key="thumb_url"
        )

    with col2:
        st.write("")
        st.write("")
        get_thumb_button = st.button("🖼️ Get Thumbnail", type="primary", use_container_width=True)

    if get_thumb_button and thumb_url:
        video_id = extract_video_id(thumb_url)

        if not video_id:
            st.error("Invalid YouTube URL. Please enter a valid URL.")
            return

        st.success(f"Video ID: {video_id}")

        # Available thumbnail qualities
        qualities = {
            "Max Resolution (1920x1080)": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "High Quality (480x360)": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "Medium Quality (320x180)": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
            "Standard Quality (120x90)": f"https://img.youtube.com/vi/{video_id}/default.jpg",
        }

        st.divider()

        # Display thumbnails
        for quality_name, thumbnail_url in qualities.items():
            st.subheader(quality_name)

            col_img, col_btn = st.columns([3, 1])

            with col_img:
                try:
                    st.image(thumbnail_url, use_container_width=True)
                except:
                    st.warning(f"Could not load {quality_name}")

            with col_btn:
                st.write("")
                st.write("")
                st.markdown(f"[⬇️ Download]({thumbnail_url})")

    elif get_thumb_button and not thumb_url:
        st.warning("Please enter a YouTube URL")

def audio_tab():
    """Audio extraction tab"""
    st.header("🎵 Audio Extractor")
    st.markdown("Extract and play audio from YouTube videos using yt-dlp")

    # Main content
    col1, col2 = st.columns([3, 1])

    with col1:
        video_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL",
            key="audio_url"
        )

    with col2:
        st.write("")
        st.write("")
        extract_button = st.button("🎵 Extract Audio", type="primary", use_container_width=True)

    if extract_button and video_url:
        with st.spinner("Extracting audio information..."):
            # First get video info
            info_data = get_video_info(video_url)

            if "error" in info_data:
                st.error(f"Error: {info_data['error']}")
            else:
                # Display video information
                st.divider()

                col_thumb, col_info = st.columns([1, 2])

                with col_thumb:
                    if info_data.get("thumbnail"):
                        st.image(info_data["thumbnail"], use_container_width=True)

                with col_info:
                    st.subheader(info_data.get("title", "Unknown Title"))

                    meta_col1, meta_col2 = st.columns(2)
                    with meta_col1:
                        st.metric("Duration", format_duration(info_data.get("duration")))
                        if info_data.get("uploader"):
                            st.write(f"**Uploader:** {info_data['uploader']}")

                    with meta_col2:
                        if info_data.get("viewCount"):
                            st.metric("Views", f"{info_data['viewCount']:,}")
                        if info_data.get("uploadDate"):
                            date_str = info_data['uploadDate']
                            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                            st.write(f"**Upload Date:** {formatted_date}")

                # Now extract audio
                st.divider()
                with st.spinner("Extracting audio URL..."):
                    audio_data = extract_audio_info(video_url)

                    if "error" in audio_data:
                        st.error(f"Error extracting audio: {audio_data['error']}")
                    elif audio_data.get("videoId"):
                        st.success("Audio extracted successfully!")

                        # Display audio information
                        with st.expander("Audio Information", expanded=True):
                            info_col1, info_col2, info_col3 = st.columns(3)

                            with info_col1:
                                st.write(f"**Format:** {audio_data.get('extension', 'N/A').upper()}")
                                st.write(f"**Quality:** {audio_data.get('quality', 'N/A')}")

                            with info_col2:
                                abr = audio_data.get('abr', 0)
                                st.write(f"**Bitrate:** {abr} kbps" if abr else "**Bitrate:** N/A")
                                asr = audio_data.get('asr', 0)
                                st.write(f"**Sample Rate:** {asr} Hz" if asr else "**Sample Rate:** N/A")

                            with info_col3:
                                filesize = audio_data.get('filesize', 0)
                                if filesize:
                                    size_mb = filesize / (1024 * 1024)
                                    st.write(f"**File Size:** {size_mb:.2f} MB")
                                else:
                                    st.write("**File Size:** N/A")

                        # Audio player using proxy stream
                        st.subheader("🔊 Audio Player")
                        video_id = audio_data.get("videoId")

                        # Use proxy URL instead of direct YouTube URL
                        stream_url = f"{API_URL}/api/audio/stream/{video_id}"

                        # Download audio with progress tracking
                        progress_bar = st.progress(0, text="Preparing to download...")
                        status_text = st.empty()

                        try:
                            # Start streaming request in a thread-like manner
                            # The API will start downloading, we poll progress
                            import threading
                            import queue

                            result_queue = queue.Queue()

                            def download_audio():
                                try:
                                    response = requests.get(stream_url, timeout=600)
                                    result_queue.put(('success', response.content))
                                except Exception as e:
                                    result_queue.put(('error', str(e)))

                            # Start download in background
                            download_thread = threading.Thread(target=download_audio)
                            download_thread.start()

                            # Poll for progress while downloading
                            last_status = ""
                            while download_thread.is_alive():
                                progress = get_download_progress(video_id)

                                if progress:
                                    status = progress.get('status', '')
                                    percent = progress.get('percent', 0)

                                    if status == 'downloading':
                                        downloaded = progress.get('downloaded', 0)
                                        total = progress.get('total', 0)
                                        speed = progress.get('speed', 0)
                                        eta = progress.get('eta', 0)

                                        progress_text = f"Downloading: {percent:.1f}%"
                                        if total > 0:
                                            progress_text += f" ({format_bytes(downloaded)} / {format_bytes(total)})"
                                        if speed > 0:
                                            progress_text += f" - {format_speed(speed)}"
                                        if eta > 0:
                                            mins, secs = divmod(int(eta), 60)
                                            if mins > 0:
                                                progress_text += f" - ETA: {mins}m {secs}s"
                                            else:
                                                progress_text += f" - ETA: {secs}s"

                                        progress_bar.progress(min(percent / 100, 0.95), text=progress_text)
                                        last_status = status

                                    elif status == 'processing':
                                        progress_bar.progress(0.97, text="Converting to MP3...")
                                        last_status = status

                                    elif status == 'complete':
                                        progress_bar.progress(0.99, text="Finalizing...")
                                        last_status = status

                                elif last_status == "":
                                    status_text.text("Waiting for server to start processing...")

                                time.sleep(0.3)

                            # Get result
                            download_thread.join()
                            result_type, result_data = result_queue.get()

                            if result_type == 'success':
                                progress_bar.progress(1.0, text="Complete!")
                                time.sleep(0.3)
                                progress_bar.empty()
                                status_text.empty()

                                # Display audio player
                                st.audio(result_data, format='audio/mpeg')

                                # Download button
                                title = audio_data.get('title', video_id)
                                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
                                st.download_button(
                                    label="⬇️ Download Audio",
                                    data=result_data,
                                    file_name=f"{safe_title}.mp3",
                                    mime="audio/mpeg"
                                )
                            else:
                                progress_bar.empty()
                                status_text.empty()
                                st.error(f"Error loading audio: {result_data}")

                        except Exception as e:
                            progress_bar.empty()
                            status_text.empty()
                            st.error(f"Error loading audio: {str(e)}")
                    else:
                        st.error("No video ID found in the response")

    elif extract_button and not video_url:
        st.warning("Please enter a YouTube URL")

def get_transcript(video_url):
    """Get video transcript"""
    try:
        response = requests.post(
            f"{API_URL}/api/transcript",
            json={"url": video_url},
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {"error": error_data.get("error", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


# ===== LLM API Functions =====

def get_llm_status():
    """Get LLM provider availability status"""
    try:
        response = requests.get(f"{API_URL}/api/llm/status", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


def get_llm_providers():
    """Get available LLM providers and models"""
    try:
        response = requests.get(f"{API_URL}/api/llm/providers", timeout=5)
        if response.status_code == 200:
            return response.json().get("providers", [])
        return []
    except:
        return []


def summarize_transcript_api(text=None, url=None, provider=None, model=None, language="ko"):
    """Summarize transcript text using LLM API"""
    try:
        payload = {"language": language}
        if text:
            payload["text"] = text
        if url:
            payload["url"] = url
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model

        response = requests.post(
            f"{API_URL}/api/summarize/transcript",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {"error": error_data.get("error", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}


def summarize_audio_api(url, mode="whisper", provider=None, model=None, language="ko"):
    """Summarize audio using LLM API"""
    try:
        payload = {
            "url": url,
            "mode": mode,
            "language": language
        }
        if provider:
            payload["provider"] = provider
        if model:
            payload["model"] = model

        response = requests.post(
            f"{API_URL}/api/summarize/audio",
            json=payload,
            timeout=300  # 5 minutes for audio processing
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {"error": error_data.get("error", "Unknown error")}
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def transcript_tab():
    """Transcript extraction tab"""
    st.header("📝 Transcript Extractor")
    st.markdown("Extract subtitles/transcripts from YouTube videos")

    col1, col2 = st.columns([3, 1])

    with col1:
        video_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL",
            key="trans_url"
        )

    with col2:
        st.write("")
        st.write("")
        trans_button = st.button("📝 Get Transcript", type="primary", use_container_width=True)

    if trans_button and video_url:
        with st.spinner("Fetching transcript..."):
            # First get video info for title/thumb
            info_data = get_video_info(video_url)
            
            if "error" not in info_data:
                st.divider()
                col_thumb, col_info = st.columns([1, 4])
                with col_thumb:
                    if info_data.get("thumbnail"):
                        st.image(info_data["thumbnail"], use_container_width=True)
                with col_info:
                    st.subheader(info_data.get("title", "Unknown Title"))
                    st.markdown(f"**Duration:** {format_duration(info_data.get('duration'))}")

            # Get transcript
            trans_data = get_transcript(video_url)

            if "error" in trans_data:
                error_msg = trans_data.get('error', '')
                if 'No transcript' in error_msg:
                    st.warning("📭 This video has no transcript available.")
                elif 'Invalid' in error_msg or 'URL' in error_msg:
                    st.error("🔗 Invalid YouTube URL. Please check the URL and try again.")
                else:
                    st.error(f"❌ Failed to fetch transcript: {error_msg}")
            else:
                lang = trans_data.get('language', 'unknown')
                is_auto = trans_data.get('isAutoGenerated', False)
                auto_label = " (Auto-generated)" if is_auto else ""
                st.success(f"Transcript fetched successfully! Language: {lang}{auto_label}")

                full_text = trans_data.get('fullText', '')
                segments = trans_data.get('segments', [])

                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    st.download_button(
                        label="⬇️ Download Full Text (.txt)",
                        data=full_text,
                        file_name=f"transcript_{trans_data.get('videoId')}.txt",
                        mime="text/plain"
                    )
                with col_dl2:
                    # Create SRT format
                    srt_content = ""
                    for i, seg in enumerate(segments, 1):
                        start = seg.get('start', 0)
                        h, m, s = int(start // 3600), int((start % 3600) // 60), start % 60
                        srt_content += f"{i}\n{h:02d}:{m:02d}:{s:06.3f} --> {h:02d}:{m:02d}:{s+2:06.3f}\n{seg.get('text', '')}\n\n"
                    st.download_button(
                        label="⬇️ Download with Timestamps (.srt)",
                        data=srt_content,
                        file_name=f"transcript_{trans_data.get('videoId')}.srt",
                        mime="text/srt"
                    )

                with st.expander("View Transcript", expanded=True):
                    st.text_area("Content", full_text, height=400)

                # AI Summary section
                st.divider()
                st.subheader("🤖 AI Summary")

                # Store transcript in session state for summarization
                st.session_state['transcript_text'] = full_text
                st.session_state['transcript_video_id'] = trans_data.get('videoId')

                if st.button("✨ Summarize with AI", key="summarize_trans_btn", type="secondary"):
                    provider = st.session_state.get('selected_provider', 'openai')
                    model = st.session_state.get('selected_model')

                    with st.spinner("Generating summary..."):
                        result = summarize_transcript_api(
                            text=full_text,
                            provider=provider,
                            model=model,
                            language="ko"
                        )

                    if "error" in result:
                        st.error(f"❌ Summarization failed: {result['error']}")
                    else:
                        st.success(f"✅ Summary generated! (Model: {result.get('model', 'unknown')})")
                        st.markdown(result.get('summary', ''))

                        # Download summary
                        st.download_button(
                            label="⬇️ Download Summary",
                            data=result.get('summary', ''),
                            file_name=f"summary_{trans_data.get('videoId')}.md",
                            mime="text/markdown"
                        )

    elif trans_button and not video_url:
        st.warning("Please enter a YouTube URL")


def ai_summary_tab():
    """AI Summary tab - dedicated summarization interface"""
    st.header("🤖 AI Summary")
    st.markdown("Generate AI-powered summaries from YouTube videos")

    col1, col2 = st.columns([3, 1])

    with col1:
        video_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL",
            key="ai_url"
        )

    with col2:
        st.write("")
        st.write("")
        summary_mode = st.selectbox(
            "Mode",
            ["Transcript", "Audio (Whisper)", "Audio (Multimodal)"],
            key="ai_mode"
        )

    # Advanced settings
    with st.expander("Advanced Settings"):
        col_prov, col_model, col_lang = st.columns(3)

        providers = get_llm_providers()
        provider_names = [p["name"] for p in providers if p.get("available", False)]

        if not provider_names:
            provider_names = ["OpenAI", "Anthropic", "Google"]

        with col_prov:
            selected_provider_name = st.selectbox(
                "Provider",
                provider_names,
                key="ai_provider_select"
            )
            selected_provider = selected_provider_name.lower()

        with col_model:
            # Get models for selected provider
            models = []
            for p in providers:
                if p["name"].lower() == selected_provider:
                    models = [m["name"] for m in p.get("models", [])]
                    break

            if not models:
                models = ["Default"]

            selected_model_name = st.selectbox("Model", models, key="ai_model_select")

            # Map model name to ID
            selected_model = None
            for p in providers:
                if p["name"].lower() == selected_provider:
                    for m in p.get("models", []):
                        if m["name"] == selected_model_name:
                            selected_model = m["id"]
                            break

        with col_lang:
            language = st.selectbox("Output Language", ["Korean", "English"], key="ai_lang")
            lang_code = "ko" if language == "Korean" else "en"

    summarize_btn = st.button("✨ Generate Summary", type="primary", use_container_width=True)

    if summarize_btn and video_url:
        # First get video info
        with st.spinner("Fetching video info..."):
            info_data = get_video_info(video_url)

        if "error" not in info_data:
            st.divider()
            col_thumb, col_info = st.columns([1, 4])
            with col_thumb:
                if info_data.get("thumbnail"):
                    st.image(info_data["thumbnail"], use_container_width=True)
            with col_info:
                st.subheader(info_data.get("title", "Unknown Title"))
                st.markdown(f"**Duration:** {format_duration(info_data.get('duration'))}")

        # Generate summary based on mode
        if summary_mode == "Transcript":
            with st.spinner("Fetching transcript and generating summary..."):
                result = summarize_transcript_api(
                    url=video_url,
                    provider=selected_provider,
                    model=selected_model,
                    language=lang_code
                )
        else:
            mode = "whisper" if "Whisper" in summary_mode else "multimodal"
            with st.spinner(f"Processing audio ({mode})... This may take a few minutes."):
                result = summarize_audio_api(
                    url=video_url,
                    mode=mode,
                    provider=selected_provider,
                    model=selected_model,
                    language=lang_code
                )

        if "error" in result:
            st.error(f"❌ Summarization failed: {result['error']}")
        else:
            st.success(f"✅ Summary generated! (Model: {result.get('model', 'unknown')})")

            # Show transcription if available (Whisper mode)
            if result.get("transcription"):
                with st.expander("View Transcription", expanded=False):
                    st.text_area("Transcription", result["transcription"], height=200)

            # Show summary
            st.markdown("### Summary")
            st.markdown(result.get("summary", ""))

            # Download buttons
            col_dl1, col_dl2 = st.columns(2)
            video_id = extract_video_id(video_url)

            with col_dl1:
                st.download_button(
                    label="⬇️ Download Summary (Markdown)",
                    data=result.get("summary", ""),
                    file_name=f"summary_{video_id}.md",
                    mime="text/markdown"
                )

            if result.get("transcription"):
                with col_dl2:
                    st.download_button(
                        label="⬇️ Download Transcription",
                        data=result.get("transcription", ""),
                        file_name=f"transcription_{video_id}.txt",
                        mime="text/plain"
                    )

    elif summarize_btn and not video_url:
        st.warning("Please enter a YouTube URL")


def main():
    st.title("🎬 YouTube Tools")
    st.markdown("Extract audio, thumbnails, and transcripts from YouTube videos")

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This app provides YouTube video tools:
        - **Thumbnail Downloader** - Download HD thumbnails
        - **Audio Extractor** - Extract and play audio
        - **Transcript Extractor** - Get subtitles/captions
        
        Built with:
        - **Streamlit** for the UI
        - **Docker** for yt-dlp API server
        - **yt-dlp** for media extraction
        """)

        st.divider()

        # API Status Check
        st.subheader("API Status")
        try:
            health_response = requests.get(f"{API_URL}/health", timeout=5)
            if health_response.status_code == 200:
                st.success("✅ API Server is running")
            else:
                st.error("❌ API Server error")
        except:
            st.error("❌ API Server is not running")
            st.info("Start Docker container:\n```bash\ncd ytdlp-server\ndocker-compose up -d\n```")

        st.divider()

        # AI Settings
        st.subheader("🤖 AI Settings")

        llm_status = get_llm_status()
        providers = get_llm_providers()

        # Provider selection
        available_providers = [p for p in providers if p.get("available", False)]

        if available_providers:
            provider_options = {p["name"]: p["id"] for p in available_providers}
            selected_provider_name = st.selectbox(
                "LLM Provider",
                list(provider_options.keys()),
                key="sidebar_provider"
            )
            st.session_state['selected_provider'] = provider_options[selected_provider_name]

            # Model selection for selected provider
            selected_provider_data = next(
                (p for p in available_providers if p["name"] == selected_provider_name),
                None
            )
            if selected_provider_data and selected_provider_data.get("models"):
                model_options = {m["name"]: m["id"] for m in selected_provider_data["models"]}
                selected_model_name = st.selectbox(
                    "Model",
                    list(model_options.keys()),
                    key="sidebar_model"
                )
                st.session_state['selected_model'] = model_options[selected_model_name]
        else:
            st.warning("No LLM providers configured")
            st.session_state['selected_provider'] = 'openai'
            st.session_state['selected_model'] = None

        # API Key Status
        st.markdown("**API Key Status:**")
        status_cols = st.columns(3)
        with status_cols[0]:
            if llm_status.get("openai"):
                st.markdown("🟢 OpenAI")
            else:
                st.markdown("🔴 OpenAI")
        with status_cols[1]:
            if llm_status.get("anthropic"):
                st.markdown("🟢 Anthropic")
            else:
                st.markdown("🔴 Anthropic")
        with status_cols[2]:
            if llm_status.get("google"):
                st.markdown("🟢 Google")
            else:
                st.markdown("🔴 Google")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📸 Thumbnail",
        "🎵 Audio",
        "📝 Transcript",
        "🤖 AI Summary"
    ])

    with tab1:
        thumbnail_tab()

    with tab2:
        audio_tab()

    with tab3:
        transcript_tab()

    with tab4:
        ai_summary_tab()

if __name__ == "__main__":
    main()
