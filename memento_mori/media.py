# memento_mori/media.py
import os
import shutil
import hashlib
import base64
import re
import mimetypes
import magic  # python-magic library
from pathlib import Path
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
from tqdm import tqdm


class InstagramMediaProcessor:
    """
    Class for processing Instagram media files.

    This class handles:
    - Converting images to WebP format
    - Generating thumbnails for images and videos
    - Copying media files to the output directory
    """

    def __init__(self, extraction_dir, output_dir, thread_count=None):
        """Initialize the media processor with paths and options."""
        self.extraction_dir = Path(extraction_dir)
        self.output_dir = Path(output_dir)
        self.thread_count = thread_count or max(1, multiprocessing.cpu_count() - 1)

        # Create output directories
        self.media_dirs = [
            self.output_dir / "media",
            self.output_dir / "media" / "posts",
            self.output_dir / "media" / "other",
            self.output_dir / "thumbnails",
        ]

        for directory in self.media_dirs:
            directory.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.thumbnail_count = 0
        self.webp_count = 0
        self.total_size_original = 0
        self.total_size_webp = 0
        
        # Initialize filename mapping
        self.filename_map = {}

    def shorten_filename(self, original_path):
        """
        Create a shortened version of a filename while preserving extension.
        
        Args:
            original_path (str): Original file path
            
        Returns:
            str: Shortened file path
        """
        if not original_path or not isinstance(original_path, str):
            return original_path
            
        # Skip if it's already a data URI
        if original_path.startswith('data:'):
            return original_path
            
        # Check if we already have a mapping for this path
        if original_path in self.filename_map:
            return self.filename_map[original_path]
            
        # Parse the path
        path_obj = Path(original_path)
        parent_dir = path_obj.parent
        filename = path_obj.name
        extension = path_obj.suffix.lower()
        
        # Create a hash of the original filename
        filename_hash = hashlib.md5(filename.encode()).hexdigest()[:8]  # Use first 8 chars of hash
        
        # Create new filename: hash + original extension
        new_filename = f"{filename_hash}{extension}"
        
        # Create the new path
        if parent_dir == Path('.'):
            new_path = new_filename
        else:
            new_path = str(parent_dir / new_filename)
        
        # Store the mapping
        self.filename_map[original_path] = new_path
        
        return new_path

    def process_media_files(self, post_data, profile_picture):
        """Process all media files from posts and profile picture."""
        # First, fix any incorrect file extensions in the extraction directory
        print("Checking and fixing file extensions...")
        extension_stats = self.fix_file_extensions(self.extraction_dir)
        print(f"Fixed {extension_stats['fixed']} files with incorrect extensions")
        
        # Create a path mapping for quick lookups
        path_mapping = extension_stats.get("path_mapping", {})
        
        # Update profile picture path if it was fixed
        if profile_picture in path_mapping:
            profile_picture = path_mapping[profile_picture]
        
        # Process profile picture and get shortened path
        shortened_profile = self.shorten_filename(profile_picture)
        self.copy_file_to_distribution(profile_picture)
        self.generate_thumbnail(profile_picture, shortened_profile)

        # Collect all media files to process
        all_media = []
        
        # Create a deep copy of post_data to modify
        updated_post_data = {}
        
        for timestamp, post in post_data.items():
            # Create a copy of the post
            updated_post = post.copy()
            updated_media = []
            
            for media_url in post["m"]:
                # Check if this media URL was fixed
                if str(self.extraction_dir / media_url) in path_mapping:
                    # Get the new path relative to extraction_dir
                    new_full_path = path_mapping[str(self.extraction_dir / media_url)]
                    media_url = str(Path(new_full_path).relative_to(self.extraction_dir))
                
                # Add to processing list
                all_media.append(media_url)
                
                # Get shortened path
                shortened_url = self.shorten_filename(media_url)
                updated_media.append(shortened_url)
            
            # Update the post with shortened media URLs
            updated_post["m"] = updated_media
            updated_post_data[timestamp] = updated_post

        total_media = len(all_media)
        print(
            f"Processing {total_media} media files using {self.thread_count} threads..."
        )

        # Process media files in parallel using ThreadPoolExecutor with tqdm
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            list(
                tqdm(
                    executor.map(self.copy_file_to_distribution, all_media),
                    total=total_media,
                    desc="Processing media files",
                    unit="files",
                )
            )

        # Calculate space savings
        self._calculate_space_savings(post_data)

        # Return updated post data and statistics
        return {
            "updated_post_data": updated_post_data,
            "shortened_profile": shortened_profile,
            "stats": {
                "thumbnail_count": self.thumbnail_count,
                "webp_count": self.webp_count,
                "total_size_original": self.total_size_original,
                "total_size_webp": self.total_size_webp,
                "space_saved_mb": (self.total_size_original - self.total_size_webp)
                / (1024 * 1024),
                "percentage_saved": (
                    (self.total_size_original - self.total_size_webp)
                    / self.total_size_original
                    * 100
                    if self.total_size_original > 0
                    else 0
                ),
                "extension_fixes": extension_stats["fixed"],
            }
        }

    def _calculate_space_savings(self, post_data):
        """Calculate space savings from WebP conversion and other optimizations."""
        # Count thumbnails
        if (self.output_dir / "thumbnails").exists():
            self.thumbnail_count = len(
                list((self.output_dir / "thumbnails").glob("*.webp"))
            )

        # Calculate total size of original files and their optimized versions
        self.total_size_original = 0
        self.total_size_webp = 0
        
        # Track all media files that were processed
        processed_files = set()
        
        # First, add all media from posts
        for timestamp, post in post_data.items():
            for media_url in post["m"]:
                processed_files.add(media_url)
        
        # Process each file to calculate size differences
        for media_url in processed_files:
            # Get the original file path
            original_path = Path(self.extraction_dir) / media_url
            
            # Get the shortened filename
            shortened_url = self.shorten_filename(media_url)
            
            # Check if the original exists
            if original_path.exists():
                original_size = original_path.stat().st_size
                self.total_size_original += original_size
                
                # Check for WebP version first
                webp_path = self.output_dir / (shortened_url.rsplit('.', 1)[0] + '.webp')
                
                if webp_path.exists():
                    # WebP version exists
                    webp_size = webp_path.stat().st_size
                    self.total_size_webp += webp_size
                    self.webp_count += 1
                else:
                    # No WebP, check for the original format in output
                    dest_path = self.output_dir / shortened_url
                    if dest_path.exists():
                        dest_size = dest_path.stat().st_size
                        self.total_size_webp += dest_size

    def copy_file_to_distribution(self, file_path, quiet=True):
        """Copy a file to distribution, optionally converting images to WebP and generating thumbnails."""
        # Skip if it's already a data URI
        if str(file_path).startswith("data:image"):
            return True

        source = Path(self.extraction_dir) / file_path
        
        # Create shortened filename
        shortened_path = self.shorten_filename(file_path)
        destination = Path(self.output_dir) / shortened_path

        # Create directory structure if it doesn't exist
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Check if source file exists
        if not source.exists():
            if not quiet:
                print(f"Warning: Source file does not exist: {source}")
            return False

        # Check if it's an image or video
        is_image = bool(re.search(r"\.(jpg|jpeg|png|gif)$", str(file_path), re.I))
        is_video = bool(re.search(r"\.(mp4|mov|avi|webm)$", str(file_path), re.I))

        if is_image:
            # Convert image to WebP for better compression
            webp_destination = Path(
                str(destination).replace(destination.suffix, ".webp")
            )
            self.convert_to_webp(source, webp_destination, quiet)

            # Generate thumbnail
            self.generate_thumbnail(source, shortened_path, quiet)
            return True
        else:
            # Copy the file as is (for videos and other file types)
            shutil.copy2(source, destination)

            # Generate thumbnail for videos
            if is_video:
                self.generate_thumbnail(source, shortened_path, quiet)
            return True

    def convert_to_webp(self, source_path, destination_path, quiet=False):
        """Convert an image to WebP format if it results in a smaller file."""
        try:
            # Open the image
            with Image.open(source_path) as img:
                # Handle transparency
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    if img.mode != "RGBA":
                        img = img.convert("RGBA")
                else:
                    img = img.convert("RGB")

                # Save as WebP with 80% quality
                img.save(destination_path, "WEBP", quality=80)

            # Check if the WebP file is actually smaller
            original_size = source_path.stat().st_size
            webp_size = destination_path.stat().st_size

            if webp_size > 0 and webp_size < original_size:
                if not quiet:
                    print(
                        f"Converted to WebP: {source_path} (saved {(original_size - webp_size) / 1024:.2f} KB)"
                    )
                return True
            else:
                # If WebP is larger, use the original file
                if destination_path.exists():
                    destination_path.unlink()

                # Copy with original extension
                original_ext = source_path.suffix
                original_destination = Path(
                    str(destination_path).replace(".webp", original_ext)
                )
                shutil.copy2(source_path, original_destination)

                if not quiet:
                    print(f"WebP larger than original, using original: {source_path}")
                return False
        except Exception as e:
            if not quiet:
                print(f"Error converting to WebP: {str(e)}")

            # Fall back to copying the original file
            original_ext = source_path.suffix
            original_destination = Path(
                str(destination_path).replace(".webp", original_ext)
            )
            original_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, original_destination)
            return False

    def fix_file_extensions(self, directory_path):
        """
        Scan a directory for files with incorrect extensions and fix them.
        Particularly focuses on media files like HEIC files that are actually JPEGs.
        
        Args:
            directory_path (str or Path): Directory to scan for files with incorrect extensions
        
        Returns:
            dict: Statistics about the fixed files
        """
        directory_path = Path(directory_path)
        stats = {
            "total_checked": 0,
            "fixed": 0,
            "already_correct": 0,
            "errors": 0,
            "fixed_files": []
        }
        
        # Make sure we have the mime-type libraries
        try:
            # Try the libmagic binding first (common on Linux/Mac)
            mime = magic.Magic(mime=True)
        except (TypeError, AttributeError):
            try:
                # Try the alternative API (common in some python-magic implementations)
                mime = magic.open(magic.MAGIC_MIME_TYPE)
                mime.load()
            except (AttributeError, TypeError):
                print("Error initializing python-magic. Please install it:")
                print("pip install python-magic")
                if os.name == "nt":  # Windows
                    print("Windows users also need to install the binary from: https://github.com/ahupp/python-magic#windows")
                return stats
        
        # Mapping of MIME types to extensions
        mime_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/heic": ".heic",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/webm": ".webm"
        }
        
        # List of media MIME type prefixes we want to process
        media_mime_prefixes = ["image/", "video/"]
        
        print(f"Scanning {directory_path} for files with incorrect extensions...")
        
        # Find all files recursively
        for file_path in tqdm(list(directory_path.glob("**/*.*")), desc="Checking files"):
            stats["total_checked"] += 1
            
            try:
                # Skip directories
                if file_path.is_dir():
                    continue
                
                # Skip non-media files based on extension
                current_ext = file_path.suffix.lower()
                if current_ext in ['.json', '.txt', '.srt', '.csv', '.html', '.xml', '.md']:
                    stats["already_correct"] += 1
                    continue
                    
                # Get the current extension and mime type
                # Handle different magic library interfaces
                try:
                    # First approach (libmagic binding)
                    file_mime = mime.from_file(str(file_path))
                except AttributeError:
                    # Second approach (alternative API)
                    file_mime = mime.file(str(file_path))
                
                # Skip if not a media file
                if not any(file_mime.startswith(prefix) for prefix in media_mime_prefixes):
                    stats["already_correct"] += 1
                    continue
                
                # Get the correct extension for this mime type
                correct_ext = mime_to_ext.get(file_mime)
                
                if correct_ext is None:
                    # If we don't have a mapping for this mime type, use mimetypes
                    correct_ext = mimetypes.guess_extension(file_mime) or current_ext
                
                # If extensions don't match, rename the file
                if correct_ext != current_ext:
                    new_path = file_path.with_suffix(correct_ext)
                    
                    # Avoid overwriting existing files
                    counter = 1
                    while new_path.exists():
                        new_stem = f"{file_path.stem}_{counter}"
                        new_path = file_path.with_stem(new_stem).with_suffix(correct_ext)
                        counter += 1
                    
                    # Rename the file
                    file_path.rename(new_path)
                    
                    stats["fixed"] += 1
                    stats["fixed_files"].append({
                        "old_path": str(file_path),
                        "new_path": str(new_path),
                        "old_type": current_ext,
                        "new_type": correct_ext
                    })
                    
                    # Don't print each fixed file to keep output clean
                else:
                    stats["already_correct"] += 1
                    
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                stats["errors"] += 1
        
        # Print summary
        if stats["fixed"] > 0:
            print(f"\n🔧 EXTENSION CORRECTION")
            print(f"   Fixed {stats['fixed']} media files with incorrect extensions")
            # Group fixes by type for a cleaner summary
            fixes_by_type = {}
            for item in stats["fixed_files"]:
                key = f"{item['old_type']} → {item['new_type']}"
                if key not in fixes_by_type:
                    fixes_by_type[key] = 0
                fixes_by_type[key] += 1
            
            # Print summary by type
            for fix_type, count in fixes_by_type.items():
                print(f"   • {count} files: {fix_type}")
        else:
            print(f"\n✓ All {stats['already_correct']} media files had correct extensions")
        
        if stats["errors"] > 0:
            print(f"   ⚠️ Errors: {stats['errors']}")
        
        # Add a path mapping to the stats
        stats["path_mapping"] = {item["old_path"]: item["new_path"] for item in stats["fixed_files"]}
        
        return stats

    def generate_thumbnail(self, source_path, relative_path, quiet=False):
        """Generate a thumbnail for an image or video file."""
        # Ensure source_path is a Path object
        source_path = (
            Path(source_path) if not isinstance(source_path, Path) else source_path
        )

        # Create thumbnails directory
        thumbs_dir = self.output_dir / "thumbnails"
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename for the thumbnail
        thumb_filename = hashlib.md5(str(relative_path).encode()).hexdigest() + ".webp"
        thumb_path = thumbs_dir / thumb_filename

        # Skip if thumbnail already exists
        if thumb_path.exists():
            return thumb_path

        # Target dimensions for square thumbnail
        target_width = 292
        target_height = 292

        try:
            # Check if file exists
            if not source_path.exists():
                if not quiet:
                    print(f"File not found: {source_path}")
                return None

            # Determine if it's a video
            is_video = bool(re.search(r"\.(mp4|mov|avi|webm)$", str(source_path), re.I))

            if is_video:
                # Try using OpenCV for video thumbnail
                try:
                    import cv2

                    video = cv2.VideoCapture(str(source_path))
                    if not video.isOpened():
                        raise Exception(f"Could not open video: {source_path}")

                    # Get video properties
                    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = video.get(cv2.CAP_PROP_FPS)

                    # Get frame from 1 second in or middle of video
                    target_frame = (
                        min(int(fps), total_frames // 2)
                        if fps > 0
                        else total_frames // 2
                    )
                    video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

                    success, frame = video.read()
                    video.release()

                    if not success:
                        raise Exception(f"Failed to extract frame from video")

                    # Convert to RGB and create PIL image
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)

                except (ImportError, Exception) as e:
                    if not quiet:
                        print(f"Video thumbnail error: {str(e)}")

                    # Create video placeholder if extraction fails
                    svg = (
                        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
                        '<rect width="400" height="400" fill="#333333"/>'
                        '<circle cx="200" cy="200" r="60" fill="#ffffff" fill-opacity="0.8"/>'
                        '<polygon points="180,160 180,240 240,200" fill="#333333"/>'
                        "</svg>"
                    )

                    return None
            else:
                # For images, use PIL
                img = Image.open(source_path)

            # Get original dimensions
            original_width, original_height = img.size

            # Calculate dimensions for cropping to 1:1 aspect ratio (center crop)
            if original_width > original_height:
                src_x = (original_width - original_height) // 2
                src_y = 0
                src_w = original_height
                src_h = original_height
            else:
                src_x = 0
                src_y = (original_height - original_width) // 2
                src_w = original_width
                src_h = original_width

            # Crop and resize
            img = img.crop((src_x, src_y, src_x + src_w, src_y + src_h))
            img = img.resize((target_width, target_height), Image.LANCZOS)

            # Save as WebP
            img.save(thumb_path, "WEBP", quality=80)

            return thumb_path

        except Exception as e:
            if not quiet:
                print(f"Error generating thumbnail: {str(e)}")
            return None
