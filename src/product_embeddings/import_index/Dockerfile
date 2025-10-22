# Dockerfile

FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY import_index/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY import_index/. .
COPY shared/. ./shared

# Set the entrypoint
ENTRYPOINT ["python", "main.py"]
