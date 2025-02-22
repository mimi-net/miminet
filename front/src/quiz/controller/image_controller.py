import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from PIL import Image
import logging

UPLOAD_FOLDER = "static/quiz_images"

ALLOWED_EXTENSIONS = {"bmp", "png", "jpg", "jpeg"}

image_routes = Blueprint("image_routes", __name__)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def check_image_with_pil(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify() 
        return True
    except (IOError, SyntaxError):
        return False

@image_routes.route('/quiz/images/<filename>')
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@image_routes.route('/quiz/upload', methods=['POST'])
def upload_image_endpoint():
    if 'file' not in request.files:
        return jsonify({"error": "No file field in form-data"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(file_path)

    if not check_image_with_pil(file_path):
        os.remove(file_path) 
        return jsonify({"error": "File is not a valid image"}), 400

    return jsonify({"filename": unique_filename}), 201
