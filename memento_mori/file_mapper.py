# memento_mori/file_mapper.py
from pathlib import Path
import json
import os


def _looks_like_profile(data):
    """True if parsed JSON matches Instagram's personal_information.json shape."""
    try:
        entry = data["profile_user"][0]
        return (
            isinstance(entry, dict)
            and "value" in entry.get("string_map_data", {}).get("Username", {})
        )
    except (KeyError, TypeError, IndexError):
        return False


def _looks_like_posts(data):
    """
    True if parsed JSON matches Instagram's posts_*.json shape: a list of post
    objects (or {"posts": [...]}), where entries have a non-empty "media" list
    and/or a "creation_timestamp".
    """
    if isinstance(data, dict) and "posts" in data:
        data = data["posts"]
    if not isinstance(data, list) or not data:
        return False
    sample = data[:5]
    return any(
        isinstance(item, dict)
        and (
            (isinstance(item.get("media"), list) and item["media"])
            or "creation_timestamp" in item
        )
        for item in sample
    )


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
			"**/personal_information/personal_information/personal_information.json",  # Double-nested (newer exports)
			"**/personal_information/personal_information.json",
			"**/account_information/personal_information.json",
			"**/personal_information.json",
			"**/*/personal_information.json"
		],
		"location": [
			"**/personal_information/information_about_you/profile_based_in.json",  # Newer exports
			"**/information_about_you/profile_based_in.json",
			"**/profile_based_in.json",
			"**/*/profile_based_in.json",
			"**/account_information/profile_based_in.json",
			"**/personal_information/profile_based_in.json"
		],
        "followers": [
            "**/connections/followers_and_following/followers*.json",
            "**/followers_and_following/followers*.json",
            "**/followers*.json",
            # Search in any subdirectory
            "**/*/followers*.json"
        ],
        "stories": [
            "**/content/stories*.json",
            "**/media/stories*.json",
            "**/your_instagram_activity/stories*.json",
            "**/stories*.json",
            "**/your_instagram_activity/stories/stories*.json",
            "**/your_instagram_activity/content/stories*.json",
            # Search in any subdirectory
            "**/*/stories*.json"
        ],
        # Add more patterns as needed
    }

    # Read window for content-sniffing (see discover_by_content): not a size
    # cap that excludes files, just how many bytes of each .json file we look
    # at. Large files are still sniffed via a truncated-prefix parse.
    SNIFF_READ_BYTES = 5 * 1024 * 1024  # 5 MB

    # File types that can be found by content when glob patterns find nothing.
    CONTENT_SNIFFERS = {
        "profile": _looks_like_profile,
        "posts": _looks_like_posts,
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

        # Fallback: for types we know how to recognize by content, try that
        # only if glob-pattern discovery came up empty. Instagram has renamed
        # export folders repeatedly over time; the JSON content shape has
        # stayed stable, so this survives future renames without a patch.
        for file_type in self.CONTENT_SNIFFERS:
            if not self.file_map.get(file_type):
                self.discover_by_content(file_type)

        return self.file_map

    @staticmethod
    def _parse_sniff_chunk(chunk):
        """
        Parse a (possibly truncated) prefix of a JSON file for content-sniffing.

        Tries a direct parse first, which succeeds whenever the whole file fit
        inside the read window. If that fails because the real file is larger
        than the window, falls back to recovering as many complete top-level
        array elements as possible using the stdlib decoder's raw_decode (which
        correctly walks nested objects/strings/escapes, unlike naive string
        splitting), so large files can still be sniffed without reading them
        in full.
        """
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            pass

        start = chunk.find("[")
        if start == -1:
            return None

        decoder = json.JSONDecoder()
        idx = start + 1
        n = len(chunk)
        items = []
        while idx < n:
            while idx < n and chunk[idx] in " \t\r\n,":
                idx += 1
            if idx >= n:
                break
            try:
                obj, end = decoder.raw_decode(chunk, idx)
            except json.JSONDecodeError:
                break
            items.append(obj)
            idx = end

        return items or None

    def discover_by_content(self, file_type):
        """
        Fallback for when glob-pattern discovery finds nothing: scan every
        .json file under base_dir and test its *parsed content* against the
        signature registered in CONTENT_SNIFFERS for file_type. Populates
        self.file_map[file_type] (and f"{file_type}_all" on multiple matches)
        exactly like discover_files() does, so no other code needs to change.

        Returns the matched path, or None.
        """
        sniffer = self.CONTENT_SNIFFERS.get(file_type)
        if sniffer is None:
            return None

        matches = []
        for json_path in self.base_dir.rglob("*.json"):
            try:
                if not json_path.is_file():
                    continue
                with open(json_path, "r", encoding="utf-8") as f:
                    chunk = f.read(self.SNIFF_READ_BYTES)
            except (OSError, UnicodeDecodeError):
                continue

            data = self._parse_sniff_chunk(chunk)
            if data is None:
                continue

            if sniffer(data):
                matches.append(json_path)

        if not matches:
            return None

        # Weak tiebreak among content-confirmed candidates only: prefer a
        # path whose name hints at the type (helps e.g. posts vs. stories,
        # which can share a similar {media, creation_timestamp} shape).
        matches.sort(key=lambda p: 0 if file_type in p.name.lower() else 1)

        print(
            f"   [content-scan] found '{file_type}' by content, not filename: "
            f"{matches[0].relative_to(self.base_dir)}"
        )
        if len(matches) > 1:
            print(
                f"   [content-scan] {len(matches)} files matched the '{file_type}' "
                f"signature; using the first, all stored in '{file_type}_all'"
            )

        self.file_map[file_type] = str(matches[0])
        if len(matches) > 1:
            self.file_map[f"{file_type}_all"] = [str(m) for m in matches]

        return self.file_map[file_type]

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

        if not self.file_map.get(file_type) and file_type in self.CONTENT_SNIFFERS:
            self.discover_by_content(file_type)

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
