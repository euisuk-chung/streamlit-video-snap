import streamlit as st
import requests
import re
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="YouTube Tools",
    page_icon="🎬",
    layout="wide"
)

# API endpoint (localhost for Docker)
API_URL = "http://localhost:8080"

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
                    elif audio_data.get("audioUrl"):
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

                        # Audio player
                        st.subheader("🔊 Audio Player")
                        audio_url = audio_data["audioUrl"]

                        try:
                            # Use st.audio with the direct URL
                            st.audio(audio_url)

                            # Provide download link
                            st.markdown(f"[⬇️ Download Audio]({audio_url})")

                        except Exception as e:
                            st.error(f"Error playing audio: {str(e)}")
                            st.info(f"You can still try to play it directly: {audio_url}")
                    else:
                        st.error("No audio URL found in the response")

    elif extract_button and not video_url:
        st.warning("Please enter a YouTube URL")

def main():
    st.title("🎬 YouTube Tools")
    st.markdown("Extract audio and download thumbnails from YouTube videos")

    # Sidebar
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This app provides YouTube video tools:
        - **Thumbnail Downloader** - Download HD thumbnails
        - **Audio Extractor** - Extract and play audio

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

    # Tabs
    tab1, tab2 = st.tabs(["📸 Thumbnail Downloader", "🎵 Audio Extractor"])

    with tab1:
        thumbnail_tab()

    with tab2:
        audio_tab()

if __name__ == "__main__":
    main()
