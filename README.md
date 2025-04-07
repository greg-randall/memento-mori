# Memento Mori - Instagram Archive Viewer

## Overview

**Memento Mori** is a tool that converts your Instagram data export into a beautiful, standalone viewer that resembles the Instagram interface. The name "Memento Mori" (Latin for "remember that you will die") reflects the ephemeral nature of our digital content. You can see an example at [gregr.org/instagram](https://gregr.org/instagram/).

![Memento Mori Interface Preview](preview.gif)

## ⚠️ IMPORTANT SECURITY WARNING ⚠️

**DO NOT** share your raw Instagram export online! It contains sensitive data you probably don't want to share:
- Phone numbers
- Precise location data
- Personal messages
- Email addresses
- Other private information

Only share the generated output folder after processing with this tool.


## How It Works

Memento Mori processes your Instagram data export and generates a static site with your posts, copying all your media files into an organized structure that can be viewed offline or hosted on your own website.

## Features
- Displays your posts in a familiar Instagram-like grid
- Shows post details, like counts, and impression statistics when clicking on a post
- Supports multiple images per post with carousel navigation
- Plays videos with native controls
- Fully responsive design that works on mobile and desktop
- Converts images to WebP format for smaller file sizes (when beneficial)
- Generates thumbnails for faster loading
- Creates video thumbnails for better preview
- Sorts posts by newest, oldest, most likes, most comments, most views, or randomly
- Shareable links to specific posts and images
- Copies all your media files to the distribution folder, maintaining the original structure

## How to Use Memento Mori

### 1. Get Your Instagram Data

1. Request and download your Instagram data archive
2. Place the zip within the folder of this repo

### 2. Preferred Method: Using Docker (Easiest)

Docker Compose is the easiest way to run Memento Mori without installing any dependencies:

```bash
# Build the Docker image
docker-compose build

# Run with default settings
docker-compose run --rm memento-mori

# Run with specific arguments
docker-compose run --rm memento-mori --output /output/my-insta-site --quality 90
```

By default, Docker will:
- Search for Instagram exports in the project directory
- Output the generated site to the './output' directory

### 3. Alternative Method: Direct Python Installation

If you prefer running the tool directly without Docker:

```bash
# Install package and dependencies
pip install -e .

# Or install dependencies manually
pip install Pillow==11.1.0 tqdm==4.67.1 jinja2==3.1.6 opencv-python==4.11.0.86

# Run the CLI
python -m memento_mori.cli
```

### CLI Arguments

The CLI supports the following arguments:

```
Options:
  --input PATH         Path to Instagram data (ZIP or folder). If not specified, auto-detection will be used.
  --output PATH        Output directory for generated website [default: ./output]
  --threads INTEGER    Number of parallel processing threads [default: auto]
  --search-dir PATH    Directory to search for Instagram exports when auto-detecting [default: current directory]
  --quality INTEGER    WebP conversion quality (1-100) [default: 80]
  --thumbnail-size WxH Size of thumbnails [default: 292x292]
  --no-auto-detect     Disable auto-detection (requires --input to be specified)
```

Note: Auto-detection is enabled by default and will look for Instagram exports in the current directory. Use `--no-auto-detect` if you want to disable this feature and specify an input path manually.

### Example Commands

```bash
# Auto-detect Instagram export in current directory
python -m memento_mori.cli

# Specify input file/folder and output directory
python -m memento_mori.cli --input path/to/instagram-export.zip --output my-instagram-site

# Use specific number of threads and image quality
python -m memento_mori.cli --threads 8 --quality 90

# Specify search directory for auto-detection
python -m memento_mori.cli --search-dir ~/Downloads

# Use custom thumbnail size
python -m memento_mori.cli --thumbnail-size 400x400

# Disable auto-detection (requires specifying input)
python -m memento_mori.cli --no-auto-detect --input path/to/instagram-export.zip
```

## Key Features

- **Auto-detection**: Memento Mori will automatically look for Instagram archive ZIP files or extracted folders in the specified directory. The ZIP file can be placed anywhere within the project folder and it will be discovered.
- **Multi-threading**: Process media files in parallel for faster conversion using multiple CPU cores.
- **WebP Conversion**: Convert images to WebP format when it results in smaller file sizes for better performance.
- **Thumbnail Generation**: Generate thumbnails for images and videos to improve loading performance.

## Viewing Your Generated Site

After the tool finishes processing your Instagram data:

1. The website will be generated in the output directory (default: ./output)
2. Open the `index.html` file in this directory with your web browser to view your Instagram archive
3. You can also upload the entire output directory to a web hosting service to share it online

## PHP Version (Alternative)

For those who prefer the original PHP implementation:

```bash
# Run from command line
php index.php
```

The PHP version may be easier to run on shared hosting environments and doesn't require additional packages if PHP is already installed with the necessary extensions.

## Troubleshooting

- If you see errors about GD library or WebP support, you may need to install additional PHP extensions
- For video thumbnail generation, ensure FFmpeg is installed and accessible in your system path
- For HEIC file support, ensure ImageMagick is installed
- If using Docker, ensure you have permissions to write to the output directory
- For large archives, be patient as processing media files can take time

## Why This Exists

Instagram, like many social platforms, has undergone significant "enshittification" - a term coined to describe how platforms evolve:

1. First, they attract users with a quality experience
2. Then, they leverage their position to extract data and attention
3. Finally, they degrade the user experience to maximize profit

When requesting your data from Instagram, the export you receive contains all your content but in a format that's intentionally difficult to navigate and enjoy. Memento Mori solves this problem by transforming your archive into an intuitive, familiar interface that brings your memories back to life.