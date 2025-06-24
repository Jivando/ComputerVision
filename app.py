import os
import subprocess
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from ultralytics import YOLO
import cv2
import uuid
import shutil

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed_videos'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

model = YOLO('best.pt')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return redirect(request.url)
    video_file = request.files['video']
    if video_file.filename == '':
        return redirect(request.url)

    if video_file:
        original_filename_base, original_extension = os.path.splitext(video_file.filename)
        unique_filename = str(uuid.uuid4()) + original_extension
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        video_file.save(video_path)

        # processed_video_path akan menjadi tempat output YOLOv8 atau fallback asli
        processed_video_path = os.path.join(app.config['PROCESSED_FOLDER'], f"yolov8_output_{unique_filename}")


        results = model.predict(source=video_path, save=True, project='runs/detect', name='predict')
        yolov8_output_dir = None
        if results and hasattr(results[0], 'save_dir'):
            yolov8_output_dir = results[0].save_dir

        actual_yolov8_output_video_path = None
        if yolov8_output_dir and os.path.exists(yolov8_output_dir):
            for file_in_output in os.listdir(yolov8_output_dir):
                if unique_filename.replace(original_extension, '') in file_in_output and \
                   (file_in_output.endswith('.mp4') or file_in_output.endswith('.avi') or \
                    file_in_output.endswith('.mov') or file_in_output.endswith('.webm')):
                    
                    actual_yolov8_output_video_path = os.path.join(yolov8_output_dir, file_in_output)
                    break

        if actual_yolov8_output_video_path and os.path.exists(actual_yolov8_output_video_path):
            shutil.move(actual_yolov8_output_video_path, processed_video_path)
            print(f"YOLOv8 output moved to: {processed_video_path}")
        else:
            print(f"Warning: YOLOv8 processed video not found. Using original video as FFmpeg input.")
            shutil.copy(video_path, processed_video_path) # Fallback to original for FFmpeg input

        # --- START FFmpeg Processing (Revised for Maximum Web Compatibility) ---
        # Tentukan path file output akhir. Pastikan ekstensi selalu .mp4 untuk kompatibilitas.
        final_video_filename = f"final_web_compatible_{original_filename_base}.mp4" 
        final_video_path = os.path.join(app.config['PROCESSED_FOLDER'], final_video_filename)

        # File yang akan diproses oleh FFmpeg (bisa jadi hasil YOLOv8 atau fallback asli)
        ffmpeg_input_path = processed_video_path

        # Perintah FFmpeg untuk memindahkan MOOV atom ke awal, re-encode ke H.264/AAC,
        # dan memastikan format pixel yang kompatibel.
        ffmpeg_command = [
            'ffmpeg', '-y', # -y: Menimpa file output yang sudah ada tanpa konfirmasi
            '-i', ffmpeg_input_path, # Input file
            '-movflags', 'faststart', # CRITICAL: Memindahkan MOOV atom ke awal file untuk streaming cepat
            '-preset', 'medium',      # Keseimbangan antara kecepatan encoding dan ukuran/kualitas file.
            '-crf', '23',             # Constant Rate Factor: Mengontrol kualitas video.
            '-c:v', 'libx264',        # Wajibkan codec video H.264 (paling kompatibel di web)
            '-pix_fmt', 'yuv420p',    # Wajibkan format pixel YUV 4:2:0 (paling kompatibel)
            '-c:a', 'aac',            # Wajibkan codec audio AAC (paling kompatibel di web)
            '-b:a', '128k',           # Bitrate audio 128kbps (umum untuk web)
            final_video_path          # Output file
        ]

        try:
            print(f"Running FFmpeg command: {' '.join(ffmpeg_command)}")
            subprocess.run(ffmpeg_command, check=True, capture_output=True, text=True)
            print(f"FFmpeg processing successful: {ffmpeg_input_path} -> {final_video_path}")
            
            # Hapus file intermediate (hasil YOLOv8 yang belum di-ffmpeg)
            if os.path.exists(processed_video_path) and processed_video_path != final_video_path:
                os.remove(processed_video_path)
            
            processed_video_path_for_display = final_video_path # Update path ke file yang sudah di-FFmpeg

        except subprocess.CalledProcessError as e:
            print(f"Error during FFmpeg processing:")
            print(f"  Command: {' '.join(e.cmd)}")
            print(f"  Return Code: {e.returncode}")
            print(f"  STDOUT: {e.stdout}")
            print(f"  STDERR: {e.stderr}")
            print("FFmpeg failed to process the video. Displaying raw YOLOv8 output (might not play in browser).")
            # Jika FFmpeg gagal, gunakan file dari YOLOv8 (processed_video_path) untuk ditampilkan/download
            processed_video_path_for_display = processed_video_path
        except FileNotFoundError:
            print("Error: FFmpeg executable not found. Please ensure FFmpeg is installed and added to your system's PATH environmental variable.")
            return "Server processing error: FFmpeg not found.", 500
        # --- END FFmpeg Processing ---

        # Clean up the original uploaded file
        if os.path.exists(video_path):
            os.remove(video_path)
        
        # Clean up the YOLOv8 run directory
        if yolov8_output_dir and os.path.exists(yolov8_output_dir):
            try:
                shutil.rmtree(yolov8_output_dir)
                parent_predict_dir = os.path.dirname(yolov8_output_dir)
                if os.path.exists(parent_predict_dir) and not os.listdir(parent_predict_dir):
                    os.rmdir(parent_predict_dir)
                
                parent_detect_dir = os.path.dirname(parent_predict_dir)
                if os.path.exists(parent_detect_dir) and not os.listdir(parent_detect_dir):
                    os.rmdir(parent_detect_dir)
            except OSError as e:
                print(f"Error removing YOLOv8 output directory: {e}")

        return render_template('result.html', video_filename=os.path.basename(processed_video_path_for_display))

    return redirect(url_for('index'))

@app.route('/processed_videos/<filename>')
def serve_processed_video(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)