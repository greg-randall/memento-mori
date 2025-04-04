#!/usr/bin/env python3
import os
import json
import shutil
import hashlib
import base64
import re
import time
from datetime import datetime
import sys
from pathlib import Path
import subprocess
from PIL import Image
import io
import threading
import argparse
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# Create distribution directory if it doesn't exist
if not os.path.exists('distribution'):
    os.makedirs('distribution', mode=0o755, exist_ok=True)

def copy_media_files(post_data, profile_picture, thread_count=None):
    """
    Copy media files to the distribution folder using multiple threads
    
    Args:
        post_data: The post data containing media URLs
        profile_picture: The profile picture URL
        thread_count: Number of threads to use (default: CPU count - 1)
    """
    if thread_count is None:
        thread_count = max(1, multiprocessing.cpu_count() - 1)
    
    # Create media directories in distribution folder
    media_dirs = [
        'distribution/media',
        'distribution/media/posts',
        'distribution/media/other',
        'distribution/thumbnails'
    ]
    
    for directory in media_dirs:
        if not os.path.exists(directory):
            os.makedirs(directory, mode=0o755, exist_ok=True)
    
    # Copy profile picture
    copy_file_to_distribution(profile_picture)
    
    # Make sure the profile picture exists in the distribution folder
    profile_dest = os.path.join('distribution', profile_picture)
    if not os.path.exists(profile_dest):
        print(f"Profile picture not found at {profile_dest}, trying direct copy...", file=sys.stderr)
        if os.path.exists(profile_picture):
            os.makedirs(os.path.dirname(profile_dest), exist_ok=True)
            shutil.copy2(profile_picture, profile_dest)
            print(f"Copied profile picture directly to {profile_dest}", file=sys.stderr)
    
    # Generate thumbnail for profile picture
    generate_thumbnail(profile_picture, profile_picture)
    
    # Collect all media files to process
    all_media = []
    for timestamp, post in post_data.items():
        for media_url in post['media']:
            all_media.append(media_url)
    
    total_media = len(all_media)
    print(f"Generating thumbnails for {total_media} media files using {thread_count} threads...", file=sys.stderr)
    
    # Process media files in parallel using a thread pool with tqdm progress bar
    def process_media_file(media_url):
        copy_file_to_distribution(media_url, quiet=True)
    
    # Use ThreadPoolExecutor with tqdm to process files in parallel
    print(f"Processing media files...", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        list(tqdm(executor.map(process_media_file, all_media), 
                 total=total_media, 
                 desc="Processing media files", 
                 unit="files"))
    
    # Log summary of conversion operations
    print(f"Finished processing {total_media} media files", file=sys.stderr)
    
    # Count how many thumbnails and WebP conversions were successfully generated
    thumbnail_count = 0
    webp_count = 0
    total_size_original = 0
    total_size_webp = 0
    
    if os.path.isdir('distribution/thumbnails'):
        thumbnail_count = len([f for f in os.listdir('distribution/thumbnails') if f.endswith('.webp')])
    
    # Count WebP conversions and calculate space savings
    print("Calculating space savings from WebP conversion...", file=sys.stderr)
    webp_items = []
    for timestamp, post in post_data.items():
        for media_url in post['media']:
            if re.search(r'\.(jpg|jpeg|png|gif)$', media_url, re.I):
                webp_items.append((media_url, re.sub(r'\.(jpg|jpeg|png|gif)$', '.webp', media_url, flags=re.I)))
    
    for original_path, webp_path in tqdm(webp_items, desc="Checking WebP conversions", unit="file"):
        if os.path.exists(os.path.join('distribution', webp_path)):
            webp_count += 1
            
            # Calculate size difference if original exists
            if os.path.exists(original_path):
                original_size = os.path.getsize(original_path)
                webp_size = os.path.getsize(os.path.join('distribution', webp_path))
                total_size_original += original_size
                total_size_webp += webp_size
    
    # Calculate total space savings
    space_saved_mb = (total_size_original - total_size_webp) / (1024 * 1024)
    
    print("All media files and thumbnails processed.", file=sys.stderr)
    print(f"Successfully generated {thumbnail_count} thumbnails.", file=sys.stderr)
    print(f"Successfully converted {webp_count} images to WebP format.", file=sys.stderr)
    print(f"Total space saved: {space_saved_mb:.2f} MB ({(total_size_original - total_size_webp) / total_size_original * 100:.1f}% if original > 0 else 0)%", file=sys.stderr)
    print("Media files copied to distribution folder.")

def copy_file_to_distribution(file_path, quiet=False):
    """
    Copy a single file to the distribution folder, maintaining its path structure
    
    Args:
        file_path: The path to the file
        quiet: Whether to suppress output messages
    """
    # Skip if it's already a data URI
    if file_path.startswith('data:image'):
        return
    
    source = file_path
    destination = os.path.join('distribution', file_path)
    
    # Create directory structure if it doesn't exist
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    # Check if source file exists
    if not os.path.exists(source):
        if not quiet:
            print(f"Warning: Source file does not exist: {source}", file=sys.stderr)
        return
    
    # Check if it's an image file that can be converted to WebP
    is_image = bool(re.search(r'\.(jpg|jpeg|png|gif)$', file_path, re.I))
    is_video = bool(re.search(r'\.(mp4|mov|avi|webm)$', file_path, re.I))
    
    if is_image and os.path.exists(source):
        # Convert image to WebP for better compression
        webp_destination = re.sub(r'\.(jpg|jpeg|png|gif)$', '.webp', destination, flags=re.I)
        convert_to_webp(source, webp_destination, quiet)
        
        # Generate thumbnail for this file
        generate_thumbnail(source, file_path, quiet)
    elif os.path.exists(source):
        # Copy the file as is (for videos and other file types)
        shutil.copy2(source, destination)
        
        # Generate thumbnail for this file
        generate_thumbnail(source, file_path, quiet)

def convert_to_webp(source_path, destination_path, quiet=False):
    """
    Convert an image to WebP format without cropping
    
    Args:
        source_path: The source image path
        destination_path: The destination WebP path
        quiet: Whether to suppress output messages
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Open the image
        with Image.open(source_path) as img:
            # Convert to RGB if needed (for PNG with transparency)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Need to preserve alpha channel
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
            else:
                # No alpha channel needed
                img = img.convert('RGB')
            
            # Save as WebP with 80% quality
            img.save(destination_path, 'WEBP', quality=80)
        
        # Check if the WebP file is actually smaller than the original
        original_size = os.path.getsize(source_path)
        webp_size = os.path.getsize(destination_path)
        
        if webp_size > 0 and webp_size < original_size:
            if not quiet:
                print(f"Converted to WebP: {source_path} (saved {(original_size - webp_size) / 1024:.2f} KB)", file=sys.stderr)
            return True
        else:
            # If WebP is larger or failed, use the original file
            os.unlink(destination_path)
            # Use the original file extension instead of hardcoding to jpg
            original_ext = os.path.splitext(source_path)[1]
            original_destination = re.sub(r'\.webp$', original_ext, destination_path)
            shutil.copy2(source_path, original_destination)
            if not quiet:
                print(f"WebP larger than original, using original: {source_path}", file=sys.stderr)
            return False
    except Exception as e:
        if not quiet:
            print(f"Error converting to WebP: {str(e)}", file=sys.stderr)
        # Fall back to copying the original file with its original extension
        original_ext = os.path.splitext(source_path)[1]
        original_destination = re.sub(r'\.webp$', original_ext, destination_path)
        shutil.copy2(source_path, original_destination)
        return False

def generate_thumbnail(source_path, relative_path, quiet=False):
    """
    Generate a thumbnail for an image or video file using Python libraries
    
    Args:
        source_path: The source file path
        relative_path: The relative path for naming the thumbnail
        quiet: Whether to suppress output messages
    
    Returns:
        str or None: The path to the generated thumbnail or None if failed
    """
    # Create thumbnails directory if it doesn't exist
    thumbs_dir = 'distribution/thumbnails'
    if not os.path.exists(thumbs_dir):
        os.makedirs(thumbs_dir, exist_ok=True)
    
    # Generate a unique filename for the thumbnail based on the original path
    thumb_filename = hashlib.md5(relative_path.encode()).hexdigest() + '.webp'
    thumb_path = os.path.join(thumbs_dir, thumb_filename)
    
    # Skip if thumbnail already exists
    if os.path.exists(thumb_path):
        return thumb_path
    
    # Target dimensions
    target_width = 292
    target_height = 292
    
    try:
        # Check if file exists
        if not os.path.exists(source_path):
            if not quiet:
                print(f"File not found: {source_path}", file=sys.stderr)
            return None
        
        # Determine file type
        is_video = bool(re.search(r'\.(mp4|mov|avi|webm)$', source_path, re.I))
        
        if is_video:
            # For videos, use OpenCV to extract a frame
            try:
                import cv2
                
                # Open the video file
                video = cv2.VideoCapture(source_path)
                
                # Check if video opened successfully
                if not video.isOpened():
                    print(f"Could not open video: {source_path}", file=sys.stderr)
                    return None
                
                # Get video properties
                total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = video.get(cv2.CAP_PROP_FPS)
                
                # Try to get a frame from 1 second in, or the middle if it's a short video
                target_frame = min(int(fps), total_frames // 2) if fps > 0 else total_frames // 2
                
                # Set the frame position
                video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                
                # Read the frame
                success, frame = video.read()
                
                # Release the video capture object
                video.release()
                
                if not success:
                    print(f"Failed to extract frame from video: {source_path}", file=sys.stderr)
                    return None
                
                # Convert BGR to RGB (OpenCV uses BGR by default)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create PIL Image from the frame
                img = Image.fromarray(frame_rgb)
                
                # Get original dimensions
                original_width, original_height = img.size
                
                # Calculate dimensions for cropping to ensure 1:1 aspect ratio
                if original_width > original_height:
                    # Landscape image: crop from the center horizontally
                    src_x = (original_width - original_height) // 2
                    src_y = 0
                    src_w = original_height
                    src_h = original_height
                else:
                    # Portrait image: crop from the center vertically
                    src_x = 0
                    src_y = (original_height - original_width) // 2
                    src_w = original_width
                    src_h = original_width
                
                # Crop the image
                img = img.crop((src_x, src_y, src_x + src_w, src_y + src_h))
                
                # Resize to target dimensions
                img = img.resize((target_width, target_height), Image.LANCZOS)
                
                # Save as WebP
                img.save(thumb_path, 'WEBP', quality=80)
                
                return thumb_path
                
            except ImportError:
                print("OpenCV (cv2) is not installed. Cannot generate video thumbnails.", file=sys.stderr)
                print("Install it with: pip install opencv-python", file=sys.stderr)
                return None
            except Exception as e:
                print(f"Error generating video thumbnail: {str(e)}", file=sys.stderr)
                return None
        else:
            # For images, use PIL
            try:
                with Image.open(source_path) as img:
                    # Get original dimensions
                    original_width, original_height = img.size
                    
                    # Calculate dimensions for cropping to ensure 1:1 aspect ratio
                    # We'll take the center portion of the image
                    if original_width > original_height:
                        # Landscape image: crop from the center horizontally
                        src_x = (original_width - original_height) // 2
                        src_y = 0
                        src_w = original_height
                        src_h = original_height
                    else:
                        # Portrait image: crop from the center vertically
                        src_x = 0
                        src_y = (original_height - original_width) // 2
                        src_w = original_width
                        src_h = original_width
                    
                    # Crop the image
                    img = img.crop((src_x, src_y, src_x + src_w, src_y + src_h))
                    
                    # Resize to target dimensions
                    img = img.resize((target_width, target_height), Image.LANCZOS)
                    
                    # Save as WebP
                    img.save(thumb_path, 'WEBP', quality=80)
                    
                    return thumb_path
            except Exception as e:
                print(f"Error processing image: {str(e)}", file=sys.stderr)
                return None
    except Exception as e:
        print(f"Error generating thumbnail: {str(e)}", file=sys.stderr)
        return None
    
    return None

def render_instagram_grid(post_data, lazy_after=30):
    """
    Render the Instagram grid HTML
    
    Args:
        post_data: The post data
        lazy_after: Number of images to load eagerly before using lazy loading
    
    Returns:
        str: The HTML for the grid
    """
    output = ''
    
    # Process each post
    i = 1
    for timestamp, post in post_data.items():
        if i > lazy_after:
            lazy_load = ' loading="lazy"'
        else:
            lazy_load = ''
        
        index = post['post_index']
        media_count = len(post['media'])
        
        # Determine which media to use for the grid thumbnail
        display_media = ''
        is_video = False
        
        if post['media'] and len(post['media']) > 0:
            first_media = post['media'][0]
            original_media = first_media
            display_media = first_media
            
            # Check if first media is a video
            is_video = bool(re.search(r'\.(mp4|mov|avi|webm)$', first_media, re.I))
            
            # Check if we have a thumbnail for this media
            thumb_filename = hashlib.md5(first_media.encode()).hexdigest() + '.webp'
            thumb_path = os.path.join('thumbnails', thumb_filename)
            
            if os.path.exists(os.path.join('distribution', thumb_path)):
                # Use the thumbnail instead of the original
                display_media = thumb_path
                print(f"Using thumbnail for: {first_media}", file=sys.stderr)
            else:
                # Check if we have a WebP version of the original image
                if not is_video:
                    webp_path = re.sub(r'\.(jpg|jpeg|png|gif)$', '.webp', first_media, flags=re.I)
                    if os.path.exists(os.path.join('distribution', webp_path)):
                        display_media = webp_path
                        print(f"Using WebP version for: {first_media}", file=sys.stderr)
                
                # If it's a video, look for a thumbnail among all media items
                if is_video:
                    found_thumbnail = False
                    
                    # First check if there are any image files in the post's media that could be thumbnails
                    for media_item in post['media']:
                        if re.search(r'\.(jpg|jpeg|png|webp|gif)$', media_item, re.I):
                            # Check if we have a thumbnail for this image
                            img_thumb_filename = hashlib.md5(media_item.encode()).hexdigest() + '.webp'
                            img_thumb_path = os.path.join('thumbnails', img_thumb_filename)
                            
                            if os.path.exists(os.path.join('distribution', img_thumb_path)):
                                display_media = img_thumb_path
                            else:
                                display_media = media_item
                            found_thumbnail = True
                            break
                    
                    # If no thumbnail found, use a better SVG placeholder
                    if not found_thumbnail:
                        # Create a simple SVG with a play button
                        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
                        svg += '<rect width="400" height="400" fill="#333333"/>'
                        svg += '<circle cx="200" cy="200" r="60" fill="#ffffff" fill-opacity="0.8"/>'
                        svg += '<polygon points="180,160 180,240 240,200" fill="#333333"/>'
                        svg += '</svg>'
                        
                        # Encode the SVG properly for use in an img src attribute
                        display_media = 'data:image/svg+xml;base64,' + base64.b64encode(svg.encode()).decode()
        
        output += f'        <div class="grid-item" data-index="{index}">\n'
        output += f'          <img src="{display_media}" alt="Instagram post"{lazy_load}>\n'
        
        # Add video indicator if it's a video
        if is_video:
            output += '          <div class="video-indicator">▶ Video</div>\n'
        
        if media_count > 1:
            output += f'          <div class="multi-indicator">⊞ {media_count}</div>\n'
        elif 'Likes' in post and post['Likes'] != '':
            output += f'          <div class="likes-indicator">♥ {post["Likes"]}</div>\n'
        
        output += '        </div>\n'
        i += 1
    
    return output

def extract_relevant_data(combined_data):
    """
    Extract relevant data from the combined Instagram data
    
    Args:
        combined_data: The combined post and insights data
    
    Returns:
        dict: Simplified data structure with relevant information
    """
    simplified_data = {}

    for index, item in enumerate(combined_data):
        # Initialize a new post entry
        post_entry = {
            'post_index': index,
            'media': [],
            'creation_timestamp_unix': "",
            'creation_timestamp_readable': "",
            'title': "",
            'Impressions': "",
            'Likes': "",
            'Comments': ""
        }
        
        # Extract post-level data
        if 'post_data' in item:
            if 'creation_timestamp' in item['post_data']:
                post_entry['creation_timestamp_unix'] = item['post_data']['creation_timestamp']
            elif 'media' in item['post_data'] and len(item['post_data']['media']) > 0 and 'creation_timestamp' in item['post_data']['media'][0]:
                # Fallback to first media item timestamp if post timestamp not available
                post_entry['creation_timestamp_unix'] = item['post_data']['media'][0]['creation_timestamp']

            post_entry['creation_timestamp_readable'] = datetime.utcfromtimestamp(
                post_entry['creation_timestamp_unix']
            ).strftime("%B %d, %Y \\at %I:%M %p")
            
            if 'title' in item['post_data']:
                post_entry['title'] = item['post_data']['title']
            
            # Extract media URIs
            if 'media' in item['post_data']:
                for media in item['post_data']['media']:
                    if 'uri' in media:
                        post_entry['media'].append(media['uri'])
                    else:
                        post_entry['media'].append("")
        
        # Get insights data if available
        if 'insights' in item and item['insights'] and 'string_map_data' in item['insights']:
            insights = item['insights']['string_map_data']
            
            # Extract specific metrics and ensure they're integers or blank
            if 'Impressions' in insights:
                impressions = insights['Impressions'].get('value', "")
                # Validate and convert to integer if numeric, otherwise leave blank
                post_entry['Impressions'] = int(impressions) if impressions and impressions.isdigit() else ""
            
            if 'Likes' in insights:
                likes = insights['Likes'].get('value', "")
                # Validate and convert to integer if numeric, otherwise leave blank
                post_entry['Likes'] = int(likes) if likes and likes.isdigit() else ""
            
            if 'Comments' in insights:
                comments = insights['Comments'].get('value', "")
                # Validate and convert to integer if numeric, otherwise leave blank
                post_entry['Comments'] = int(comments) if comments and comments.isdigit() else ""
        
        simplified_data[post_entry['creation_timestamp_unix']] = post_entry
    
    # Sort by timestamp (newest first)
    return dict(sorted(simplified_data.items(), key=lambda x: x[0], reverse=True))

def verify_images_in_html(html_content):
    """
    Verify that all images referenced in the HTML actually exist
    
    Args:
        html_content: The HTML content to check
    """
    # Extract all image sources from the HTML
    image_sources = re.findall(r'<img[^>]+src=([\'"])([^"\']+)\\1', html_content)
    
    # Get just the src values
    image_sources = [src for _, src in image_sources]
    total_images = len(image_sources)
    missing_images = 0
    fixed_images = 0
    
    print(f"Found {total_images} image references to verify.", file=sys.stderr)
    
    # Use tqdm for progress tracking
    for src in tqdm(image_sources, desc="Verifying images", unit="img"):
        # Skip data URIs
        if src.startswith('data:image'):
            continue
        
        # Check if the image exists in the distribution folder
        image_path = os.path.join('distribution', src)
        
        if not os.path.exists(image_path):
            missing_images += 1
            print(f"Missing image: {src}", file=sys.stderr)
            
            # Try to find the image with a different extension
            base_path = os.path.join(os.path.dirname(image_path), os.path.splitext(os.path.basename(image_path))[0])
            found = False
            
            # Check common image extensions
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                alt_path = base_path + ext
                if os.path.exists(alt_path):
                    print(f"  Found alternative: {os.path.basename(alt_path)}", file=sys.stderr)
                    
                    # Copy the file to the expected path
                    shutil.copy2(alt_path, image_path)
                    fixed_images += 1
                    found = True
                    break
            
            if not found:
                # Check if the original file exists (before distribution)
                original_src = src
                if os.path.exists(original_src):
                    print(f"  Found original file, copying to distribution: {original_src}", file=sys.stderr)
                    
                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    
                    # Copy the file
                    shutil.copy2(original_src, image_path)
                    fixed_images += 1
    
    # Report results
    if missing_images == 0:
        print("All images verified successfully!", file=sys.stderr)
    else:
        print(f"Found {missing_images} missing images, fixed {fixed_images}.", file=sys.stderr)
        if missing_images > fixed_images:
            print(f"WARNING: {missing_images - fixed_images} images could not be fixed.", file=sys.stderr)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process Instagram data and generate a static website.')
    parser.add_argument('--threads', type=int, default=max(1, multiprocessing.cpu_count() - 1),
                        help='Number of threads to use for processing (default: CPU count - 1)')
    args = parser.parse_args()
    
    # Set the thread count for later use
    thread_count = args.threads
    print(f"Using {thread_count} threads for processing", file=sys.stderr)
    
    # Set timezone
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    
    # Load personal information
    with open("personal_information/personal_information/personal_information.json", 'r') as f:
        personal_data = json.load(f)
    
    profile_picture = personal_data['profile_user'][0]['media_map_data']['Profile Photo']['uri']
    user_name = personal_data['profile_user'][0]["string_map_data"]["Username"]["value"]
    
    # Load location data
    with open("personal_information/information_about_you/profile_based_in.json", 'r') as f:
        location_data = json.load(f)
    
    location = location_data['inferred_data_primary_location'][0]['string_map_data']['City Name']['value']
    
    # Load and decode the JSON files
    with open('logged_information/past_instagram_insights/posts.json', 'r') as f:
        insights_data = json.load(f)
    
    with open('your_instagram_activity/content/posts_1.json', 'r') as f:
        post_data = json.load(f)
    
    # Create an indexed array of insights data using creation_timestamp as key
    indexed_insights = {}
    for insight in insights_data['organic_insights_posts']:
        timestamp = insight['media_map_data']['Media Thumbnail']['creation_timestamp']
        indexed_insights[timestamp] = insight
    
    # Combine the data
    combined_data = []
    for post in post_data:
        # Get the timestamp from the first media item (since a post might have multiple media items)
        timestamp = post['media'][0]['creation_timestamp']
        
        # Create the combined post object
        combined_post = {
            'post_data': post,
            'insights': indexed_insights.get(timestamp)
        }
        
        # Add to combined data array
        combined_data.append(combined_post)
    
    # Extract relevant data
    post_data = extract_relevant_data(combined_data)
    
    # Get first and last timestamps for display
    keys = list(post_data.keys())
    first_key = keys[0]  # Newest post (already sorted)
    last_key = keys[-1]  # Oldest post
    
    # Format timestamps
    last_timestamp = datetime.utcfromtimestamp(int(first_key)).strftime("%B %Y")
    first_timestamp = datetime.utcfromtimestamp(int(last_key)).strftime("%B %Y")
    
    # Copy media files and generate thumbnails first
    copy_media_files(post_data, profile_picture, thread_count)
    
    # Generate HTML content
    html_content = f'''
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memento Mori</title>
    <link rel="stylesheet" href="style.css">
    <!-- Script to make post data available to JavaScript -->
    <script>
        window.postData = {json.dumps(post_data)};
        
        // Function to copy the current URL to clipboard
        function copyCurrentUrl() {{
            const url = window.location.href;
            navigator.clipboard.writeText(url)
                .then(() => {{
                    alert('Link copied to clipboard!');
                }})
                .catch(err => {{
                    console.error('Could not copy URL: ', err);
                }});
        }}
    </script>
    <script>
{open('modal.js', 'r').read()}
    </script>
  </head>
  <body class="vsc-initialized">
    <header>
      <div class="header-content">
        <a href="https://github.com/greg-randall/memento-mori" class="logo">Memento Mori</a>
        <div class="date-range-header" id="date-range-header">{first_timestamp} - {last_timestamp}</div>
      </div>
    </header>
    <main>
      <div class="loading" id="loadingPosts" style="display: none;"> Loading posts... </div>
      <div class="profile-info">
        <div class="profile-picture">
          <img alt="Profile Picture" src="{profile_picture}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
        </div>
        <div class="profile-details">
          <h1 id="username">{user_name}</h1>
          <div class="stats">
            <div class="stat">
              <span class="stat-count" id="post-count">{len(post_data)}</span> posts
            </div>
          </div>
        </div>
      </div>
      <div class="sort-options">
        <div class="sort-row">
          <a href="#" class="sort-link active" data-sort="newest">Newest</a>
          <a href="#" class="sort-link" data-sort="oldest">Oldest</a>
          <a href="#" class="sort-link" data-sort="most-likes">Most Likes</a>
          <a href="#" class="sort-link" data-sort="most-comments">Most Comments</a>
          <a href="#" class="sort-link" data-sort="most-views">Most Views</a>
          <a href="#" class="sort-link" data-sort="random">Random</a>
        </div>
      </div>
      <div class="posts-grid" id="postsGrid">
{render_instagram_grid(post_data)}
      </div>
       
    </main>

    <!-- Modal for post details -->
    <div class="post-modal" id="postModal">
        <div class="close-modal" id="closeModal">✕</div>
        <div class="modal-nav modal-prev" id="modalPrev">❮</div>
        <div class="modal-nav modal-next" id="modalNext">❯</div>
        <div class="post-modal-content">
            <div class="post-media" id="postMedia"></div>
            <div class="post-info">
                <div class="post-header">
                    <div class="post-user" id="postUserPic">
                        <img src="{profile_picture}" alt="Profile" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                    </div>
                    <div class="post-username" id="postUsername">{user_name}</div>
                </div>
                <div class="post-caption" id="postCaption"></div>
                <div class="post-stats" id="postStats"></div>
                <div class="post-date" id="postDate"></div>
            </div>
        </div>
    </div>
  </body>
</html>
'''
    
    # Write the HTML to the distribution folder
    with open('distribution/index.html', 'w') as f:
        f.write(html_content)
    
    # Copy the CSS file to the distribution folder
    if os.path.exists('style.css'):
        shutil.copy2('style.css', 'distribution/style.css')
        print("CSS file copied to distribution folder.", file=sys.stderr)
    
    # Verify all images in the HTML are accessible
    print("Verifying all images in the generated HTML...", file=sys.stderr)
    verify_images_in_html(html_content)
    
    print("HTML generation complete. Files are in the 'distribution' directory.")

if __name__ == "__main__":
    main()
