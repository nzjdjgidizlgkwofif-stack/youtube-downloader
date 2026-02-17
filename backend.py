from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pytube import YouTube
import os
import threading
import uuid
import tempfile
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for GitHub Pages

# Store download progress
downloads = {}

def download_video(url, download_id):
    """Background download function"""
    try:
        downloads[download_id]['status'] = 'downloading'
        downloads[download_id]['progress'] = 10
        
        # Create YouTube object
        yt = YouTube(url)
        downloads[download_id]['title'] = yt.title
        
        # Get audio stream
        audio_stream = yt.streams.filter(only_audio=True).first()
        downloads[download_id]['progress'] = 30
        
        if not audio_stream:
            raise Exception("No audio stream found")
        
        # Create temp file
        temp_dir = tempfile.mkdtemp()
        filename = f"{download_id}.mp3"
        filepath = os.path.join(temp_dir, filename)
        
        downloads[download_id]['progress'] = 50
        
        # Download
        audio_stream.download(output_path=temp_dir, filename=filename)
        downloads[download_id]['progress'] = 80
        
        # Verify file exists
        if os.path.exists(filepath):
            downloads[download_id]['filepath'] = filepath
            downloads[download_id]['status'] = 'completed'
            downloads[download_id]['progress'] = 100
        else:
            raise Exception("File not created")
            
    except Exception as e:
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = str(e)
        print(f"Error: {e}")

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

@app.route('/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    download_id = str(uuid.uuid4())
    
    downloads[download_id] = {
        'id': download_id,
        'url': url,
        'status': 'starting',
        'progress': 0,
        'title': 'Processing...'
    }
    
    # Start download in background
    thread = threading.Thread(target=download_video, args=(url, download_id))
    thread.daemon = True
    thread.start()
    
    return jsonify({'id': download_id})

@app.route('/progress/<download_id>')
def get_progress(download_id):
    if download_id in downloads:
        download_info = downloads[download_id]
        return jsonify({
            'status': download_info['status'],
            'progress': download_info.get('progress', 0),
            'title': download_info.get('title', ''),
            'error': download_info.get('error', '')
        })
    return jsonify({'status': 'not_found'}), 404

@app.route('/download-file/<download_id>')
def download_file(download_id):
    if download_id in downloads and 'filepath' in downloads[download_id]:
        filepath = downloads[download_id]['filepath']
        if os.path.exists(filepath):
            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{downloads[download_id]['title']}.mp3",
                mimetype='audio/mpeg'
            )
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
