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

Only share the generated `distribution` folder after processing with this tool.

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

## Requirements

### For PHP Version:
- PHP 7.2+ with GD library and WebP support
- Your Instagram data export (in the original folder structure)
- For video thumbnail generation: FFmpeg (optional but recommended)
- For HEIC file support: ImageMagick (optional)

### For Python Version:
- Python 3.6+
- Required Python packages: Pillow, tqdm
- For video thumbnail generation: OpenCV (`pip install opencv-python`)
- Your Instagram data export (in the original folder structure)

## How to Use

1. Request and download your Instagram data archive (Settings > Privacy and Security > Data Download)
2. Extract the archive to a folder
3. Place the Memento Mori files in the same folder as your extracted archive
4. Choose one of the following methods to run the tool:

### Using Python (Recommended):
```bash
# Install required packages
pip install pillow tqdm opencv-python

# Run the script (with progress bars)
python instagram_processor.py

# For multi-threading with specific thread count:
python instagram_processor.py --threads 8
```

### Using PHP:
```bash
# Run from command line
php index.php
```

5. A `distribution` folder will be created containing your Instagram archive viewer and media files
6. Open `distribution/index.html` in your browser or upload the entire distribution folder to your web hosting

**Note**: Processing can take significant time for large archives, especially during thumbnail generation and WebP conversion. The Python version includes progress bars to help track the process and uses multi-threading for faster processing.

## Processing Details

During processing, Memento Mori:

1. Copies all media files to the distribution folder
2. Converts images to WebP format when it results in smaller file sizes
3. Generates thumbnails for all images and videos
4. Creates a responsive HTML interface with your posts
5. Organizes everything into a clean, standalone website

## Python vs PHP Implementation

Memento Mori offers two implementation options:

### Python Version Advantages:
- Faster processing with multi-threading support
- Visual progress bars for better tracking
- Better memory management for large archives
- Easier installation of dependencies on most systems
- More detailed logging and error handling

### PHP Version Advantages:
- No additional packages required if PHP is already installed
- May be easier to run on shared hosting environments
- Familiar for users with PHP experience

Choose the implementation that works best for your environment and technical comfort level. Both versions produce identical output.

## Why This Exists

Instagram, like many social platforms, has undergone significant "enshittification" - a term coined to describe how platforms evolve:

1. First, they attract users with a quality experience
2. Then, they leverage their position to extract data and attention
3. Finally, they degrade the user experience to maximize profit

When requesting your data from Instagram, the export you receive contains all your content but in a format that's intentionally difficult to navigate and enjoy. Memento Mori solves this problem by transforming your archive into an intuitive, familiar interface that brings your memories back to life.

## Troubleshooting

- If you see errors about GD library or WebP support, you may need to install additional PHP extensions
- For video thumbnail generation, ensure FFmpeg is installed and accessible in your system path
- For HEIC file support, ensure ImageMagick is installed
