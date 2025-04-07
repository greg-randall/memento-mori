# memento_mori/media.py
import os
import shutil
import hashlib
import base64
import re
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

    def process_media_files(self, post_data, profile_picture):
        """Process all media files from posts and profile picture."""
        # Process profile picture
        self.copy_file_to_distribution(profile_picture)
        self.generate_thumbnail(profile_picture, profile_picture)

        # Collect all media files to process
        all_media = []
        for timestamp, post in post_data.items():
            for media_url in post["m"]:
                all_media.append(media_url)

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

        # Return statistics
        return {
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
        }

    def _calculate_space_savings(self, post_data):
        """Calculate space savings from WebP conversion."""
        # Count thumbnails
        if (self.output_dir / "thumbnails").exists():
            self.thumbnail_count = len(
                list((self.output_dir / "thumbnails").glob("*.webp"))
            )

        # Calculate WebP savings
        for timestamp, post in post_data.items():
            for media_url in post["m"]:
                if re.search(r"\.(jpg|jpeg|png|gif)$", str(media_url), re.I):
                    original_path = Path(self.extraction_dir) / media_url
                    webp_path = self.output_dir / re.sub(
                        r"\.(jpg|jpeg|png|gif)$", ".webp", media_url, flags=re.I
                    )

                    if webp_path.exists():
                        self.webp_count += 1

                        # Calculate size difference if original exists
                        if original_path.exists():
                            original_size = original_path.stat().st_size
                            webp_size = webp_path.stat().st_size
                            self.total_size_original += original_size
                            self.total_size_webp += webp_size

    def copy_file_to_distribution(self, file_path, quiet=True):
        """Copy a file to distribution, optionally converting images to WebP and generating thumbnails."""
        # Skip if it's already a data URI
        if str(file_path).startswith("data:image"):
            return True

        source = Path(self.extraction_dir) / file_path
        destination = Path(self.output_dir) / file_path

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
            self.generate_thumbnail(source, file_path, quiet)
            return True
        else:
            # Copy the file as is (for videos and other file types)
            shutil.copy2(source, destination)

            # Generate thumbnail for videos
            if is_video:
                self.generate_thumbnail(source, file_path, quiet)
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
