FROM python:3.10-slim

# Install system dependencies (including support for image processing)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
# Install the package and dependencies
RUN pip install --no-cache-dir -e .

# For environments without pyproject.toml, install dependencies directly
RUN pip install --no-cache-dir Pillow==11.1.0 tqdm==4.67.1 jinja2==3.1.6 opencv-python==4.11.0.86 ftfy==6.3.1

# Copy application code
COPY . .

# Create directories for input/output
RUN mkdir -p /input /output

# Set the entrypoint
ENTRYPOINT ["python", "-m", "memento_mori.cli"]

# Default command if none provided
CMD ["--help"]