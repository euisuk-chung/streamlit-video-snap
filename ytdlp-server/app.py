from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import yt_dlp
import logging
import re
import os
import tempfile
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                for fmt in info['formats']:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        audio_format = fmt
                        break

                # Fallback to best format with audio
                if not audio_format:
                    for fmt in info['formats']:
                        if fmt.get('acodec') != 'none':
                            audio_format = fmt
                            break

            if not audio_format:
                return jsonify({'error': 'No audio format found'}), 404

            response_data = {
                'success': True,
                'videoId': video_id,
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'audioUrl': audio_format.get('url'),
                'extension': audio_format.get('ext', 'webm'),
                'mimeType': audio_format.get('format_note', 'audio/webm'),
                'quality': audio_format.get('quality', 'unknown'),
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

if __name__ == '__main__':
    # For local development only
    app.run(host='0.0.0.0', port=8080, debug=True)
