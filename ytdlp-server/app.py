from flask import Flask, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS
import yt_dlp
import logging
import re
import requests as http_requests
from urllib.parse import quote
import tempfile
import os
import threading
import time
import uuid

# LLM Service for AI summarization
from llm_service import LLMService

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Progress tracking storage
download_progress = {}
progress_lock = threading.Lock()

# Summarization task tracking
summarize_tasks = {}
summarize_lock = threading.Lock()

# LLM Service instance
llm_service = LLMService()


class ProgressHook:
    """Progress hook for yt-dlp to track download progress"""
    def __init__(self, video_id):
        self.video_id = video_id

    def __call__(self, d):
        with progress_lock:
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0) or 0
                eta = d.get('eta', 0) or 0

                if total > 0:
                    percent = (downloaded / total) * 100
                else:
                    percent = 0

                download_progress[self.video_id] = {
                    'status': 'downloading',
                    'percent': round(percent, 1),
                    'downloaded': downloaded,
                    'total': total,
                    'speed': speed,
                    'eta': eta,
                    'updated_at': time.time()
                }
            elif d['status'] == 'finished':
                download_progress[self.video_id] = {
                    'status': 'processing',
                    'percent': 100,
                    'message': 'Converting to MP3...',
                    'updated_at': time.time()
                }
            elif d['status'] == 'error':
                download_progress[self.video_id] = {
                    'status': 'error',
                    'message': str(d.get('error', 'Unknown error')),
                    'updated_at': time.time()
                }

def extract_video_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # If already a video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    return None

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'yt-dlp-api'}), 200


@app.route('/api/progress/<video_id>', methods=['GET'])
def get_progress(video_id):
    """Get download progress for a video"""
    with progress_lock:
        if video_id in download_progress:
            progress = download_progress[video_id].copy()
            # Clean up old entries (older than 5 minutes)
            current_time = time.time()
            if current_time - progress.get('updated_at', 0) > 300:
                del download_progress[video_id]
                return jsonify({'status': 'not_found'}), 404
            return jsonify(progress), 200
        return jsonify({'status': 'not_found'}), 404


@app.route('/api/debug/<video_id>', methods=['GET'])
def debug_formats(video_id):
    """Debug endpoint to see available formats"""
    try:
        youtube_url = f'https://www.youtube.com/watch?v={video_id}'
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            formats = []
            for fmt in info.get('formats', []):
                formats.append({
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'acodec': fmt.get('acodec'),
                    'vcodec': fmt.get('vcodec'),
                    'protocol': fmt.get('protocol'),
                    'abr': fmt.get('abr'),
                    'url_prefix': fmt.get('url', '')[:100] if fmt.get('url') else None,
                })
            return jsonify({'formats': formats}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/audio', methods=['POST'])
def get_audio():
    """Extract audio information from YouTube video"""
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" in request body'}), 400

        url = data['url']
        video_id = extract_video_id(url)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL or video ID'}), 400

        # Construct full YouTube URL
        youtube_url = f'https://www.youtube.com/watch?v={video_id}'

        logger.info(f'Processing video: {video_id}')

        # yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            # Find best audio format
            audio_format = None
            if info.get('formats'):
                # First try direct HTTPS formats
                audio_formats = []
                for fmt in info['formats']:
                    protocol = fmt.get('protocol', '')
                    if protocol in ('https', 'http'):
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            audio_formats.append(fmt)

                if audio_formats:
                    audio_formats.sort(key=lambda x: x.get('abr', 0) or 0, reverse=True)
                    audio_format = audio_formats[0]

                # Fallback: any audio format (including DASH/HLS)
                if not audio_format:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                            audio_format = fmt
                            break

                # Last fallback: any format with audio
                if not audio_format:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none':
                            audio_format = fmt
                            break

            if not audio_format:
                return jsonify({'error': 'No audio format found'}), 404

            # Determine proper MIME type - will be converted to MP3 by stream/download
            ext = 'mp3'  # yt-dlp will convert to MP3
            mime_type = 'audio/mpeg'

            response_data = {
                'success': True,
                'videoId': video_id,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'extension': ext,
                'mimeType': mime_type,
                'quality': audio_format.get('format_note', 'unknown'),
                'abr': audio_format.get('abr', 0),  # Audio bitrate
                'asr': audio_format.get('asr', 0),  # Audio sample rate
                'filesize': audio_format.get('filesize', 0),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'uploadDate': info.get('upload_date'),
            }

            logger.info(f'Successfully extracted audio for: {video_id}')
            return jsonify(response_data), 200

    except yt_dlp.utils.DownloadError as e:
        logger.error(f'yt-dlp download error: {str(e)}')
        return jsonify({'error': f'Failed to extract video: {str(e)}'}), 400
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@app.route('/api/info', methods=['POST'])
def get_info():
    """Get video metadata without extracting audio URL"""
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" in request body'}), 400

        url = data['url']
        video_id = extract_video_id(url)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL or video ID'}), 400

        youtube_url = f'https://www.youtube.com/watch?v={video_id}'

        logger.info(f'Fetching info for video: {video_id}')

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)

            response_data = {
                'success': True,
                'videoId': video_id,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'uploadDate': info.get('upload_date'),
                'viewCount': info.get('view_count', 0),
                'description': info.get('description', ''),
            }

            logger.info(f'Successfully fetched info for: {video_id}')
            return jsonify(response_data), 200

    except Exception as e:
        logger.error(f'Error fetching info: {str(e)}')
        return jsonify({'error': f'Failed to fetch info: {str(e)}'}), 500

@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    """Extract transcript (subtitles) from YouTube video"""
    try:
        data = request.get_json()

        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" in request body'}), 400

        url = data['url']
        video_id = extract_video_id(url)
        preferred_lang = data.get('lang', 'ko')  # 기본값: 한국어

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL or video ID'}), 400

        logger.info(f'Fetching transcript for video: {video_id}')

        # youtube-transcript-api 사용 (yt-dlp보다 429 에러에 강함)
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt = YouTubeTranscriptApi()
        lang_priority = [preferred_lang, 'en']

        # 비디오 제목 가져오기 (별도 요청)
        title = 'Unknown'
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f'https://www.youtube.com/watch?v={video_id}', download=False)
                title = info.get('title', 'Unknown')
        except Exception:
            pass

        # 자막 가져오기
        transcript_data = ytt.fetch(video_id, languages=lang_priority)
        language = transcript_data.language
        is_auto = transcript_data.is_generated

        transcript_segments = []
        for snippet in transcript_data.snippets:
            text = snippet.text.strip()
            if text:
                transcript_segments.append({
                    'start': snippet.start,
                    'text': text
                })

        full_text = ' '.join([seg['text'] for seg in transcript_segments])

        response_data = {
            'success': True,
            'videoId': video_id,
            'title': title,
            'language': language,
            'isAutoGenerated': is_auto,
            'segments': transcript_segments,
            'fullText': full_text
        }

        logger.info(f'Successfully fetched transcript for: {video_id} (lang: {language}, auto: {is_auto})')
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f'Error fetching transcript: {str(e)}')
        return jsonify({'error': f'Failed to fetch transcript: {str(e)}'}), 500

@app.route('/api/audio/stream/<video_id>', methods=['GET'])
def stream_audio(video_id):
    """Stream audio from YouTube using yt-dlp download"""
    try:
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return jsonify({'error': 'Invalid video ID'}), 400

        youtube_url = f'https://www.youtube.com/watch?v={video_id}'
        logger.info(f'Streaming audio for video: {video_id}')

        # Initialize progress
        with progress_lock:
            download_progress[video_id] = {
                'status': 'starting',
                'percent': 0,
                'updated_at': time.time()
            }

        # Create temp file for audio
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f'{video_id}.%(ext)s')

        progress_hook = ProgressHook(video_id)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'progress_hooks': [progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Find the downloaded file
        audio_file = None
        for f in os.listdir(temp_dir):
            if f.startswith(video_id):
                audio_file = os.path.join(temp_dir, f)
                break

        if not audio_file or not os.path.exists(audio_file):
            return jsonify({'error': 'Failed to download audio'}), 500

        # Get file size for Content-Length header
        file_size = os.path.getsize(audio_file)
        ext = os.path.splitext(audio_file)[1].lstrip('.')

        mime_map = {
            'm4a': 'audio/mp4',
            'mp4': 'audio/mp4',
            'mp3': 'audio/mpeg',
            'webm': 'audio/webm',
            'opus': 'audio/opus',
            'ogg': 'audio/ogg',
        }
        mime_type = mime_map.get(ext, 'audio/mpeg')

        # Update progress to complete
        with progress_lock:
            download_progress[video_id] = {
                'status': 'complete',
                'percent': 100,
                'updated_at': time.time()
            }

        # Use send_file for proper Content-Length header (required by st.audio)
        response = send_file(
            audio_file,
            mimetype=mime_type,
            as_attachment=False,
            download_name=f'{video_id}.{ext}'
        )

        # Clean up temp file after response is sent
        @response.call_on_close
        def cleanup():
            try:
                os.remove(audio_file)
                os.rmdir(temp_dir)
            except:
                pass
            # Clean up progress after a delay
            with progress_lock:
                if video_id in download_progress:
                    del download_progress[video_id]

        return response

    except Exception as e:
        logger.error(f'Error streaming audio: {str(e)}')
        with progress_lock:
            download_progress[video_id] = {
                'status': 'error',
                'message': str(e),
                'updated_at': time.time()
            }
        return jsonify({'error': f'Failed to stream audio: {str(e)}'}), 500


@app.route('/api/audio/download/<video_id>', methods=['GET'])
def download_audio(video_id):
    """Download audio file from YouTube using yt-dlp"""
    try:
        if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
            return jsonify({'error': 'Invalid video ID'}), 400

        youtube_url = f'https://www.youtube.com/watch?v={video_id}'
        logger.info(f'Downloading audio for video: {video_id}')

        # Create temp file for audio
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, f'{video_id}.%(ext)s')

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        # Get video info for title
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            title = info.get('title', 'audio')

        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Find the downloaded file
        audio_file = None
        for f in os.listdir(temp_dir):
            if f.startswith(video_id):
                audio_file = os.path.join(temp_dir, f)
                break

        if not audio_file or not os.path.exists(audio_file):
            return jsonify({'error': 'Failed to download audio'}), 500

        # Sanitize filename
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_title:
            safe_title = video_id
        ext = os.path.splitext(audio_file)[1].lstrip('.')

        mime_map = {
            'm4a': 'audio/mp4',
            'mp4': 'audio/mp4',
            'mp3': 'audio/mpeg',
            'webm': 'audio/webm',
            'opus': 'audio/opus',
            'ogg': 'audio/ogg',
        }
        mime_type = mime_map.get(ext, 'audio/mpeg')

        # Use send_file for proper Content-Length header
        response = send_file(
            audio_file,
            mimetype=mime_type,
            as_attachment=True,
            download_name=f'{safe_title}.{ext}'
        )

        # Clean up temp file after response is sent
        @response.call_on_close
        def cleanup():
            try:
                os.remove(audio_file)
                os.rmdir(temp_dir)
            except:
                pass

        return response

    except Exception as e:
        logger.error(f'Error downloading audio: {str(e)}')
        return jsonify({'error': f'Failed to download audio: {str(e)}'}), 500


# ===== LLM API Endpoints =====

@app.route('/api/llm/status', methods=['GET'])
def get_llm_status():
    """Get availability status of all LLM providers"""
    try:
        status = llm_service.get_provider_status()
        return jsonify(status), 200
    except Exception as e:
        logger.error(f'Error getting LLM status: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/llm/providers', methods=['GET'])
def get_llm_providers():
    """Get list of available LLM providers with their models"""
    try:
        providers = llm_service.get_available_providers()
        return jsonify({'providers': providers}), 200
    except Exception as e:
        logger.error(f'Error getting LLM providers: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/summarize/transcript', methods=['POST'])
def summarize_transcript():
    """Summarize video transcript using LLM"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request body'}), 400

        # Get transcript text - either from request or fetch from URL
        text = data.get('text')
        url = data.get('url')

        if not text and not url:
            return jsonify({'error': 'Either "text" or "url" is required'}), 400

        # If URL is provided, fetch transcript first
        if not text and url:
            # Extract video ID
            video_id_match = re.search(
                r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
                url
            )
            if not video_id_match:
                return jsonify({'error': 'Invalid YouTube URL'}), 400

            video_id = video_id_match.group(1)
            video_url = f'https://www.youtube.com/watch?v={video_id}'

            # Fetch transcript using existing logic
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['ko', 'en'],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

            preferred_lang = data.get('lang', 'ko')
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})

            transcript_url = None
            for lang in [preferred_lang, 'en']:
                if lang in subtitles:
                    for fmt in subtitles[lang]:
                        if fmt.get('ext') == 'json3':
                            transcript_url = fmt.get('url')
                            break
                if transcript_url:
                    break

            if not transcript_url:
                for lang in [preferred_lang, 'en']:
                    if lang in automatic_captions:
                        for fmt in automatic_captions[lang]:
                            if fmt.get('ext') == 'json3':
                                transcript_url = fmt.get('url')
                                break
                    if transcript_url:
                        break

            if not transcript_url:
                return jsonify({'error': 'No transcript available for this video'}), 404

            import urllib.request
            import json
            with urllib.request.urlopen(transcript_url) as response:
                transcript_data = json.loads(response.read().decode('utf-8'))

            segments = []
            for event in transcript_data.get('events', []):
                if 'segs' in event:
                    text_parts = [seg.get('utf8', '') for seg in event['segs']]
                    segment_text = ''.join(text_parts).strip()
                    if segment_text:
                        segments.append(segment_text)

            text = ' '.join(segments)

        if not text:
            return jsonify({'error': 'No transcript text available'}), 400

        # Get LLM parameters
        provider = data.get('provider')
        model = data.get('model')
        language = data.get('language')

        # Summarize
        result = llm_service.summarize_transcript(text, provider, model, language)

        if 'error' in result:
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as e:
        logger.error(f'Error summarizing transcript: {str(e)}')
        return jsonify({'error': f'Failed to summarize: {str(e)}'}), 500


@app.route('/api/summarize/audio', methods=['POST'])
def summarize_audio():
    """Summarize video audio using LLM (Whisper or Multimodal)"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'Missing "url" in request body'}), 400

        url = data['url']
        mode = data.get('mode', 'whisper')  # 'whisper' or 'multimodal'
        provider = data.get('provider')
        model = data.get('model')
        language = data.get('language')

        # Extract video ID
        video_id_match = re.search(
            r'(?:youtube\.com/(?:watch\?v=|embed/|v/|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})',
            url
        )
        if not video_id_match:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        video_id = video_id_match.group(1)
        video_url = f'https://www.youtube.com/watch?v={video_id}'

        # Create task ID for tracking
        task_id = str(uuid.uuid4())

        with summarize_lock:
            summarize_tasks[task_id] = {
                'status': 'downloading',
                'percent': 0,
                'message': 'Downloading audio...'
            }

        # Download audio to temp file
        temp_dir = tempfile.mkdtemp()
        audio_file = None

        try:
            def progress_hook(d):
                with summarize_lock:
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            percent = int((downloaded / total) * 30)  # 0-30% for download
                            summarize_tasks[task_id]['percent'] = percent
                    elif d['status'] == 'finished':
                        summarize_tasks[task_id]['percent'] = 30
                        summarize_tasks[task_id]['message'] = 'Processing audio...'

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'progress_hooks': [progress_hook],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Find the downloaded file
            for file in os.listdir(temp_dir):
                if file.endswith('.mp3'):
                    audio_file = os.path.join(temp_dir, file)
                    break

            if not audio_file:
                return jsonify({'error': 'Failed to download audio'}), 500

            # Update status
            with summarize_lock:
                if mode == 'whisper':
                    summarize_tasks[task_id]['status'] = 'transcribing'
                    summarize_tasks[task_id]['percent'] = 35
                    summarize_tasks[task_id]['message'] = 'Transcribing audio with Whisper...'
                else:
                    summarize_tasks[task_id]['status'] = 'summarizing'
                    summarize_tasks[task_id]['percent'] = 35
                    summarize_tasks[task_id]['message'] = 'Analyzing audio with AI...'

            # Summarize audio
            result = llm_service.summarize_audio(audio_file, mode, provider, model, language)

            with summarize_lock:
                if 'error' in result:
                    summarize_tasks[task_id]['status'] = 'error'
                    summarize_tasks[task_id]['message'] = result['error']
                else:
                    summarize_tasks[task_id]['status'] = 'complete'
                    summarize_tasks[task_id]['percent'] = 100
                    summarize_tasks[task_id]['message'] = 'Complete'

            if 'error' in result:
                return jsonify(result), 500

            result['task_id'] = task_id
            return jsonify(result), 200

        finally:
            # Clean up temp files
            try:
                if audio_file and os.path.exists(audio_file):
                    os.remove(audio_file)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass

    except Exception as e:
        logger.error(f'Error summarizing audio: {str(e)}')
        return jsonify({'error': f'Failed to summarize audio: {str(e)}'}), 500


@app.route('/api/summarize/progress/<task_id>', methods=['GET'])
def get_summarize_progress(task_id):
    """Get progress of a summarization task"""
    with summarize_lock:
        if task_id not in summarize_tasks:
            return jsonify({'error': 'Task not found'}), 404
        return jsonify(summarize_tasks[task_id]), 200


if __name__ == '__main__':
    # For local development only
    app.run(host='0.0.0.0', port=8080, debug=True)
