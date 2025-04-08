FROM python:3.10-slim

# Install system dependencies (including support for image processing and libmagic)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libjpeg-dev \
    zlib1g-dev \
    libmagic-dev \
    file \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for input/output
RUN mkdir -p /input /output

# Set the entrypoint
ENTRYPOINT ["python", "-m", "memento_mori.cli"]

# Default command if none provided
CMD ["--help"]