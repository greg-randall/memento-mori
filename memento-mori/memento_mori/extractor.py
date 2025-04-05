# memento_mori/extractor.py
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from file_mapper import InstagramFileMapper


class InstagramArchiveExtractor:
    """
    Class for handling the extraction and validation of Instagram data archives.

    This class provides methods to:
    - Auto-detect Instagram archive files
    - Extract archives to temporary or specified locations
    - Validate the structure of extracted content
    - Clean up temporary files after processing
    """

    REQUIRED_FILES = ["profile", "location", "posts"]

    def __init__(self, input_path=None, output_path=None, cleanup=True):
        """
        Initialize the extractor with paths and options.

        Args:
            input_path (str, optional): Path to the Instagram archive (ZIP or folder)
            output_path (str, optional): Path where extracted content should be placed
            cleanup (bool): Whether to clean up temporary files after extraction
        """
        self.input_path = input_path
        self.output_path = output_path
        self.cleanup = cleanup
        self.temp_dir = None
        self.extraction_dir = None
        self.file_mapper = None
        self.file_map = {}  # Maps required file types to their actual paths

    def auto_detect_archive(self, search_dir="."):
        """
        Auto-detect Instagram archive files in the specified directory.

        Args:
            search_dir (str): Directory to search for Instagram archives

        Returns:
            str: Path to the detected archive or None if not found
        """
        # Look for ZIP files that might be Instagram archives
        potential_archives = []

        for root, _, files in os.walk(search_dir):
            for file in files:
                if file.lower().endswith(".zip"):
                    zip_path = os.path.join(root, file)
                    # Check if this ZIP might be an Instagram archive
                    if self._is_instagram_archive(zip_path):
                        potential_archives.append(zip_path)

        if not potential_archives:
            return None

        # If multiple archives found, take the most recent one
        if len(potential_archives) > 1:
            # Sort by modification time (most recent first)
            potential_archives.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            print(
                f"Multiple potential Instagram archives found. Using the most recent: {potential_archives[0]}"
            )

        self.input_path = potential_archives[0]
        return self.input_path

    def _is_instagram_archive(self, zip_path):
        """
        Check if a ZIP file is likely an Instagram archive.
        """

        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                namelist = zip_ref.namelist()

                # More flexible check - look for these directory names anywhere in the paths
                key_dirs = ["personal_information", "your_instagram_activity"]
                found_dirs = set()

                for name in namelist:
                    for dir_name in key_dirs:
                        if dir_name in name.lower():
                            found_dirs.add(dir_name)

                # If we found any of the key directories, it's probably an Instagram archive
                is_archive = len(found_dirs) > 0
                return is_archive

        except Exception as e:
            print(f"Error examining ZIP: {str(e)}")
            return False

    def extract(self):
        """
        Extract the Instagram archive to the specified location.

        Returns:
            str: Path to the extracted content

        Raises:
            ValueError: If no input path is specified or the file doesn't exist
            zipfile.BadZipFile: If the ZIP file is invalid
        """
        if not self.input_path:
            raise ValueError(
                "No input path specified. Use auto_detect_archive() or specify input_path."
            )

        if not os.path.exists(self.input_path):
            raise ValueError(f"Input path does not exist: {self.input_path}")

        # Determine if input is a ZIP file or a directory
        if os.path.isfile(self.input_path) and self.input_path.lower().endswith(".zip"):
            # Create a temporary directory if no output_path is specified
            if not self.output_path:
                self.temp_dir = tempfile.mkdtemp(prefix="instagram_export_")
                self.extraction_dir = self.temp_dir
            else:
                self.extraction_dir = self.output_path
                os.makedirs(self.extraction_dir, exist_ok=True)

            # Extract the ZIP file
            print(f"Extracting {self.input_path} to {self.extraction_dir}...")
            with zipfile.ZipFile(self.input_path, "r") as zip_ref:
                zip_ref.extractall(self.extraction_dir)
        else:
            # Input is already a directory
            self.extraction_dir = self.input_path

        # After extraction, check if there's a single directory at the top level
        contents = os.listdir(self.extraction_dir)
        if len(contents) == 1 and os.path.isdir(
            os.path.join(self.extraction_dir, contents[0])
        ):
            # If so, use that as the actual extraction directory
            self.extraction_dir = os.path.join(self.extraction_dir, contents[0])
            print(
                f"Found single top-level directory, using it as extraction dir: {self.extraction_dir}"
            )

        # Now validate with the correct path
        if self.validate_structure():
            return self.extraction_dir
        else:
            raise ValueError(
                "Extracted content does not appear to be a valid Instagram archive."
            )

    def validate_structure(self):
        """
        Validate the structure of the extracted content.
        """
        if not self.extraction_dir or not os.path.exists(self.extraction_dir):
            return False

        # Create file mapper
        self.file_mapper = InstagramFileMapper(self.extraction_dir)
        self.file_mapper.discover_all_files()

        # Validate required files
        valid, missing_files = self.file_mapper.validate_required_files(
            self.REQUIRED_FILES
        )

        if not valid:
            print(f"Missing required files: {', '.join(missing_files)}")
            return False

        # For backward compatibility, update self.file_map
        self.file_map = self.file_mapper.file_map
        return True

    def _map_important_files(self):
        """
        Find and map important files that might be in different locations.
        """
        for file_type, patterns in self.FILE_PATTERNS.items():
            # Handle both single string patterns and lists of patterns
            if isinstance(patterns, str):
                patterns = [patterns]

            all_matches = []
            for pattern in patterns:
                # Use Path.glob to find files matching each pattern
                matches = list(Path(self.extraction_dir).glob(pattern))
                all_matches.extend(matches)

            if all_matches:
                # Store the path to the first matching file
                self.file_map[file_type] = str(all_matches[0])

                # If multiple posts files are found, store them all
                if file_type == "posts" and len(all_matches) > 1:
                    self.file_map[f"{file_type}_all"] = [
                        str(match) for match in all_matches
                    ]

    def get_file_path(self, file_type):
        """
        Get the path to an important file.

        Args:
            file_type (str): Type of file to get (e.g., "posts", "insights")

        Returns:
            str: Path to the file or None if not found
        """
        return self.file_map.get(file_type)

    def cleanup_temp_files(self):
        """
        Clean up temporary files created during extraction.
        """
        if self.cleanup and self.temp_dir and os.path.exists(self.temp_dir):
            print(f"Cleaning up temporary directory: {self.temp_dir}")
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def __del__(self):
        """
        Ensure cleanup of temporary files when the object is destroyed.
        """
        self.cleanup_temp_files()
