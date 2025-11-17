# Dockerfile

FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY src/video_inventory_analysis/queue_videos/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy the source code
COPY src/video_inventory_analysis/queue_videos/. .
COPY src/shared/. ./shared

# Set the entrypoint
ENTRYPOINT ["python", "main.py"]
