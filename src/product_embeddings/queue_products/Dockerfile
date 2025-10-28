# Dockerfile

FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY src/product_embeddings/queue_products/requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copy the source code
COPY src/product_embeddings/queue_products/. .
COPY src/shared/. ./shared

# Set the entrypoint
ENTRYPOINT ["python", "main.py"]
