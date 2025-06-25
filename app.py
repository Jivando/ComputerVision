import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from ultralytics import YOLO
import uuid
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed_videos'

# Folder upload & output (HARUS sudah ada di Dockerfile)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

model = YOLO('best.pt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files or request.files['video'].filename == '':
        return redirect(request.url)

    video_file = request.files['video']
    original_filename_base, original_extension = os.path.splitext(video_file.filename)
    unique_filename = str(uuid.uuid4()) + original_extension
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    video_file.save(video_path)

    processed_video_path = os.path.join(app.config['PROCESSED_FOLDER'], f"yolov8_output_{unique_filename}")
    results = model.predict(
        source=video_path,
        save=True,
        project='/app/runs/detect',
        name='predict'
    )

    yolov8_output_dir = getattr(results[0], 'save_dir', None) if results else None
    actual_output_path = None
    if yolov8_output_dir and os.path.exists(yolov8_output_dir):
        for f in os.listdir(yolov8_output_dir):
            if unique_filename.replace(original_extension, '') in f and f.endswith(('.mp4', '.avi', '.mov', '.webm')):
                actual_output_path = os.path.join(yolov8_output_dir, f)
                break

    if actual_output_path and os.path.exists(actual_output_path):
        shutil.move(actual_output_path, processed_video_path)
    else:
        shutil.copy(video_path, processed_video_path)

    final_video_filename = f"final_{original_filename_base}.mp4"
    final_video_path = os.path.join(app.config['PROCESSED_FOLDER'], final_video_filename)
    ffmpeg_command = [
        'ffmpeg', '-y',
        '-i', processed_video_path,
        '-movflags', 'faststart',
        '-preset', 'medium',
        '-crf', '23',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        final_video_path
    ]

    try:
        subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
        if os.path.exists(processed_video_path):
            os.remove(processed_video_path)
        display_path = final_video_path
    except:
        display_path = processed_video_path

    if os.path.exists(video_path): os.remove(video_path)
    if yolov8_output_dir and os.path.exists(yolov8_output_dir):
        shutil.rmtree(yolov8_output_dir, ignore_errors=True)

    return render_template('result.html', video_filename=os.path.basename(display_path))

@app.route('/processed_videos/<filename>')
def serve_processed_video(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
