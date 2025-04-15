# memento_mori/file_mapper.py
from pathlib import Path
import os


class InstagramFileMapper:
    """
    Central class for discovering and mapping Instagram export files.
    Used by both Extractor and Loader to maintain consistency.
    """

    # Define all patterns in one central location
    FILE_PATTERNS = {
        "posts": ["**/content/posts*.json", "**/media/posts*.json"],
        "insights": ["**/past_instagram_insights/posts.json"],
        "profile": [
            "**/personal_information/personal_information.json",
            "**/account_information/personal_information.json",  # Alternative location
            "**/personal_information.json",  # Directly in root
            "**/profile_information.json"    # Alternative filename
        ],
        "location": ["**/information_about_you/profile_based_in.json"],
        # Add more patterns as needed
    }

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.file_map = {}

    def discover_all_files(self):
        """
        Discover all files defined in FILE_PATTERNS.
        """
        for file_type, patterns in self.FILE_PATTERNS.items():
            self.discover_files(file_type, patterns)
        return self.file_map

    def discover_files(self, file_type, patterns=None):
        """
        Discover files of a specific type.
        """
        if patterns is None:
            patterns = self.FILE_PATTERNS.get(file_type, [])

        # Handle both single string patterns and lists of patterns
        if isinstance(patterns, str):
            patterns = [patterns]

        all_matches = []
        for pattern in patterns:
            # First try exact path if it looks like one
            if not pattern.startswith("**"):
                exact_path = os.path.join(self.base_dir, pattern)
                if os.path.exists(exact_path):
                    all_matches.append(Path(exact_path))
                    continue

            # Otherwise use Path.glob to find files matching pattern
            matches = list(self.base_dir.glob(pattern))
            all_matches.extend(matches)

        if all_matches:
            # Store the path to the first matching file
            self.file_map[file_type] = str(all_matches[0])

            # If multiple matches are found, store them all
            if len(all_matches) > 1:
                self.file_map[f"{file_type}_all"] = [
                    str(match) for match in all_matches
                ]

        return self.file_map.get(file_type)

    def get_file_path(self, file_type):
        """
        Get the path to a specific file type.
        """
        if file_type not in self.file_map and file_type in self.FILE_PATTERNS:
            # Try to discover it if not already in the map
            self.discover_files(file_type)

        return self.file_map.get(file_type)

    def validate_required_files(self, required_files):
        """
        Validate that all required files exist.
        """
        missing_files = []
        for file_type in required_files:
            if not self.get_file_path(file_type):
                missing_files.append(file_type)

        return len(missing_files) == 0, missing_files
