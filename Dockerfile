# Gunakan image Python resmi yang ringan
FROM python:3.11-slim

# Install system dependencies: FFmpeg, Git, dan libraries OpenCV
RUN apt-get update && apt-get install -y \
    ffmpeg libsm6 libxext6 git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory ke /app
WORKDIR /app

# Copy semua file ke container
COPY . /app

# Buat folder upload, output, dan YOLO runs directory + beri permission
RUN mkdir -p /app/uploads /app/processed_videos /app/runs/detect && \
    chmod -R 777 /app/uploads /app/processed_videos /app/runs

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variable opsional untuk config Ultralytics (hindari warning)
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics

# Expose port 7860 (default port Flask di Hugging Face)
EXPOSE 7860

# Jalankan aplikasi Flask
CMD ["python", "app.py"]
