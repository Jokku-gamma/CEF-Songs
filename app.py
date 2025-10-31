from flask import Flask, jsonify, request, redirect
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import cloudinary.api
from cloudinary.exceptions import NotFound
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)  # Enable CORS for all routes

# === CLOUDINARY SETUP ===
cloudinary.config( 
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
    api_key = os.environ.get('CLOUDINARY_API_KEY'), 
    api_secret = os.environ.get('CLOUDINARY_API_SECRET'),
    secure = True
)
CLOUDINARY_ROOT_FOLDER = "song-library"
# ==========================

@app.route('/api/folders')
def list_folders():
    try:
        # 1. Get ALL resources (files) with the root folder prefix
        resources_result = cloudinary.api.resources(
            type="upload",
            prefix=CLOUDINARY_ROOT_FOLDER,
            resource_type="video",
            max_results=500
        )
        
        folders = {}
        
        for res in resources_result.get('resources', []):
            full_path = res.get('public_id')
            
            try:
                relative_path = os.path.relpath(full_path, CLOUDINARY_ROOT_FOLDER)
                folder_name = os.path.dirname(relative_path)
            except ValueError:
                continue

            if not folder_name:
                continue

            if folder_name not in folders:
                folders[folder_name] = {
                    'name': folder_name,
                    'metadata': {},
                    'audio_files': []
                }
            
            if not folders[folder_name]['metadata']:
                try:
                    metadata_str = res.get('context', {}).get('custom', {}).get('metadata', '{}')
                    folders[folder_name]['metadata'] = json.loads(metadata_str)
                except Exception as json_e:
                    print(f"JSON parse error: {json_e}")
                    folders[folder_name]['metadata'] = {"error": "invalid metadata"}

            # === FIX #1: ADD AUDIO TRANSFORMATIONS ===
            # Get the original URL
            original_url = res.get('secure_url')
            
            # Create the optimized URL
            # We split the URL at '/upload/' and insert the transformation string
            # ac_mp3 = audio codec MP3
            # br_128k = bitrate 128k
            # This makes the file small and fast
            parts = original_url.split('/upload/')
            optimized_url = parts[0] + '/upload/ac_mp3,br_128k/' + parts[1]
            # === END FIX #1 ===

            folders[folder_name]['audio_files'].append({
                'name': os.path.basename(res.get('filename', 'Unknown Name')),
                'url': optimized_url  # <-- Use the NEW optimized URL
            })

        all_folders_data = list(folders.values())
        return jsonify(all_folders_data)

    except Exception as e:
        print(f"Error listing folders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_song():
    if 'folder_name' not in request.form:
        return jsonify({'error': 'Missing folder name'}), 400
        
    folder_name = request.form['folder_name']
    metadata_str = request.form.get('metadata', '{}')
    
    instrumental = request.files.get('instrumental')
    full = request.files.get('full')
    
    if not instrumental or not full:
        return jsonify({'error': 'Missing audio files'}), 400

    uploaded_files = []
    
    try:
        context = { "metadata": metadata_str }

        # === FIX #2: Remove extension from public_id ===
        inst_filename_base, inst_ext = os.path.splitext(secure_filename(instrumental.filename))
        inst_public_id = f"{CLOUDINARY_ROOT_FOLDER}/{folder_name}/{inst_filename_base}"
        # === END FIX #2 ===
        
        inst_result = cloudinary.uploader.upload(
            instrumental,
            resource_type="video",
            public_id=inst_public_id,
            context=context,
            overwrite=True
        )
        uploaded_files.append(inst_result.get('secure_url'))
        
        # === FIX #2: Remove extension from public_id ===
        full_filename_base, full_ext = os.path.splitext(secure_filename(full.filename))
        full_public_id = f"{CLOUDINARY_ROOT_FOLDER}/{folder_name}/{full_filename_base}"
        # === END FIX #2 ===

        full_result = cloudinary.uploader.upload(
            full,
            resource_type="video",
            public_id=full_public_id,
            context=context,
            overwrite=True
        )
        uploaded_files.append(full_result.get('secure_url'))

        return jsonify({
            'success': True,
            'folder': folder_name,
            'files': uploaded_files
        })
            
    except Exception as e:
        print(f"Error on upload: {str(e)}")
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# Serve index.html for the root route
@app.route('/')
def serve_app():
    return app.send_static_file('index.html')

# Error handler
@app.errorhandler(Exception)
def handle_error(error):
    print(f"Error: {str(error)}")
    response = { "error": str(error), "status": "error" }
    return jsonify(response), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)