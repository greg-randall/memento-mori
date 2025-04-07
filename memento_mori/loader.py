# memento_mori/loader.py
import json
import re
from datetime import datetime
import html
from ftfy import fix_text


def fix_double_encoded_utf8(text):
    """
    Fix double-encoded UTF-8 sequences in text using ftfy.
    This handles cases where UTF-8 characters (like emoji) were incorrectly encoded twice.
    """
    if not isinstance(text, str):
        return text
    
    # Use ftfy to fix the text encoding issues
    return fix_text(text)


class InstagramDataLoader:
    """
    Class for loading and processing Instagram data from the exported archive.

    This class provides methods to:
    - Load JSON files (posts, insights, user data)
    - Parse and merge data sources
    - Convert timestamps and format data
    - Provide a clean data structure for the generator
    """

    def __init__(self, extraction_dir, file_mapper=None):
        """
        Initialize the loader with the path to the extracted data.

        Args:
            extraction_dir (str): Path to the extracted Instagram data
            file_mapper (InstagramFileMapper, optional): File mapper from extractor
        """
        self.extraction_dir = extraction_dir
        self.file_mapper = file_mapper

        # If no file mapper was provided, create one
        if self.file_mapper is None:
            from .file_mapper import InstagramFileMapper

            self.file_mapper = InstagramFileMapper(extraction_dir)
            self.file_mapper.discover_all_files()

        # Storage for loaded data
        self.profile_data = None
        self.location_data = None
        self.posts_data = None
        self.insights_data = None
        self.combined_data = None

    def load_profile_data(self):
        """
        Load user profile data.

        Returns:
            dict: User profile information
        """
        profile_path = self.file_mapper.get_file_path("profile")
        if not profile_path:
            print("Profile data not found")
            return {"username": "Unknown", "profile_picture": ""}

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                self.profile_data = json.load(f)

            profile_info = {
                "username": self.profile_data["profile_user"][0]["string_map_data"][
                    "Username"
                ]["value"],
                "profile_picture": self.profile_data["profile_user"][0][
                    "media_map_data"
                ]["Profile Photo"]["uri"],
            }

            return profile_info
        except Exception as e:
            print(f"Error loading profile data: {str(e)}")
            return {"username": "Unknown", "profile_picture": ""}

    def load_location_data(self):
        """
        Load user location data.

        Returns:
            dict: User location information
        """
        location_path = self.file_mapper.get_file_path("location")
        if not location_path:
            print("Location data not found")
            return {"location": "Unknown"}

        try:
            with open(location_path, "r", encoding="utf-8") as f:
                self.location_data = json.load(f)

            location_info = {
                "location": self.location_data["inferred_data_primary_location"][0][
                    "string_map_data"
                ]["City Name"]["value"]
            }

            return location_info
        except Exception as e:
            print(f"Error loading location data: {str(e)}")
            return {"location": "Unknown"}

    def load_posts_data(self):
        """
        Load posts data from one or more posts JSON files.

        Returns:
            list: Combined posts data from all posts files
        """
        all_posts = []

        # Check if we have multiple post files
        post_paths = []
        if self.file_mapper.file_map.get("posts_all"):
            post_paths = self.file_mapper.file_map["posts_all"]
        elif self.file_mapper.get_file_path("posts"):
            post_paths = [self.file_mapper.get_file_path("posts")]

        if not post_paths:
            print("No posts data found")
            return []

        for posts_path in post_paths:
            try:
                with open(posts_path, "r", encoding="utf-8") as f:
                    # Read the file content first
                    file_content = f.read()
                    
                    # Fix encoding issues with ftfy
                    file_content = fix_text(file_content)
                    
                    # Parse the modified content
                    posts_data = json.loads(file_content, strict=False)
                    all_posts.extend(posts_data)
            except Exception as e:
                print(f"Error loading posts data from {posts_path}: {str(e)}")

        self.posts_data = all_posts
        return all_posts

    def load_insights_data(self):
        """
        Load insights data.

        Returns:
            dict: Insights data indexed by timestamp
        """
        insights_path = self.file_mapper.get_file_path("insights")
        if not insights_path:
            print(
                "Warning: No insights file found. Insights data will not be available."
            )
            return {}

        try:
            with open(insights_path, "r", encoding="utf-8") as f:
                file_content = f.read()
                # Fix encoding issues
                file_content = fix_text(file_content)
                insights_raw = json.loads(file_content, strict=False)

            # Index insights by timestamp
            insights_indexed = {}
            
            # Handle different possible structures
            if "organic_insights_posts" in insights_raw:
                for insight in insights_raw.get("organic_insights_posts", []):
                    timestamp = None
                    
                    # Try to get timestamp from media_map_data
                    if "media_map_data" in insight and "Media Thumbnail" in insight["media_map_data"]:
                        timestamp = insight["media_map_data"]["Media Thumbnail"].get("creation_timestamp")
                    
                    # If no timestamp yet, try other fields
                    if not timestamp and "creation_timestamp" in insight:
                        timestamp = insight["creation_timestamp"]
                    
                    if timestamp:
                        insights_indexed[str(timestamp)] = insight
            else:
                # Try alternative structure
                for insight in insights_raw:
                    if isinstance(insight, dict) and "creation_timestamp" in insight:
                        timestamp = insight["creation_timestamp"]
                        insights_indexed[str(timestamp)] = insight

            self.insights_data = insights_indexed
            return insights_indexed
        except Exception as e:
            print(f"Error loading insights data: {str(e)}")
            self.insights_data = {}
            return {}

    def combine_data(self):
        """
        Combine posts and insights data.

        Returns:
            list: Combined data with posts and their associated insights
        """
        if self.posts_data is None:
            self.load_posts_data()

        if self.insights_data is None:
            self.load_insights_data()

        combined = []
        
        # Create a mapping of timestamps to insights for faster lookup
        insights_map = {}
        for timestamp, insight in self.insights_data.items():
            insights_map[str(timestamp)] = insight

        for post in self.posts_data:
            try:
                # Get the timestamp from the first media item
                timestamp = None
                if "media" in post and len(post["media"]) > 0 and "creation_timestamp" in post["media"][0]:
                    timestamp = str(post["media"][0]["creation_timestamp"])
                elif "creation_timestamp" in post:
                    timestamp = str(post["creation_timestamp"])
                
                # Find associated insights
                insight = insights_map.get(timestamp) if timestamp else None
                
                # Create combined entry
                combined.append({"post_data": post, "insights": insight})
            except (IndexError, KeyError) as e:
                print(f"Error processing post: {str(e)}")
                # Add post without insights
                combined.append({"post_data": post, "insights": None})

        self.combined_data = combined
        return combined

    def extract_relevant_data(self):
        """
        Extract relevant data from the combined posts and insights data.

        Returns:
            dict: Simplified data structure with relevant information
        """
        if self.combined_data is None:
            self.combine_data()

        simplified_data = {}

        for index, item in enumerate(self.combined_data):
            # Initialize a new post entry with shortened keys
            post_entry = {
                "i": index,  # post_index
                "m": [],     # media
                "t": "",     # creation_timestamp_unix
                "d": "",     # creation_timestamp_readable
                "tt": "",    # title
                "im": "",    # Impressions
                "l": "",     # Likes
                "c": "",     # Comments
            }

            # Extract post-level data
            if "post_data" in item:
                if "creation_timestamp" in item["post_data"]:
                    post_entry["t"] = item["post_data"]["creation_timestamp"]
                elif "media" in item["post_data"] and len(item["post_data"]["media"]) > 0 and "creation_timestamp" in item["post_data"]["media"][0]:
                    # Fallback to first media item timestamp if post timestamp not available
                    post_entry["t"] = item["post_data"]["media"][0]["creation_timestamp"]

                post_entry["d"] = datetime.utcfromtimestamp(
                    post_entry["t"]
                ).strftime("%B %d, %Y at %I:%M %p")

                # Get title from post data
                post_title = ""
                # Check for title directly in post_data
                if "title" in item["post_data"] and item["post_data"]["title"]:
                    post_title = item["post_data"]["title"]
                    if isinstance(post_title, str):
                        # Use ftfy to fix text encoding issues
                        post_title = fix_text(post_title)
                        # Then unescape HTML entities
                        post_title = html.unescape(post_title)
                
                # Check for title in media items
                if not post_title and "media" in item["post_data"]:
                    for media_item in item["post_data"]["media"]:
                        if "title" in media_item and media_item["title"]:
                            post_title = media_item["title"]
                            if isinstance(post_title, str):
                                post_title = fix_text(post_title)
                                post_title = html.unescape(post_title)
                            break  # Use the first media item with a title

                # Extract media URIs
                if "media" in item["post_data"]:
                    for media in item["post_data"]["media"]:
                        if "uri" in media:
                            post_entry["m"].append(media["uri"])
                        else:
                            post_entry["m"].append("")

            # Get insights data if available
            insights_title = ""
            if "insights" in item and item["insights"]:
                insights = item["insights"]
                
                # Try to get caption from insights
                if "string_map_data" in insights:
                    insights_data = insights["string_map_data"]
                    
                    # Extract specific metrics and ensure they're integers or blank
                    if "Impressions" in insights_data:
                        impressions = insights_data["Impressions"].get("value", "")
                        # Validate and convert to integer if numeric, otherwise leave blank
                        post_entry["im"] = int(impressions) if impressions and impressions.isdigit() else ""

                    if "Likes" in insights_data:
                        likes = insights_data["Likes"].get("value", "")
                        # Validate and convert to integer if numeric, otherwise leave blank
                        post_entry["l"] = int(likes) if likes and likes.isdigit() else ""

                    if "Comments" in insights_data:
                        comments = insights_data["Comments"].get("value", "")
                        # Validate and convert to integer if numeric, otherwise leave blank
                        post_entry["c"] = int(comments) if comments and comments.isdigit() else ""
                    
                    # Try to get caption from insights
                    if "Caption" in insights_data and insights_data["Caption"].get("value"):
                        insights_title = insights_data["Caption"].get("value", "")
                        if isinstance(insights_title, str):
                            insights_title = fix_text(insights_title)
                            insights_title = html.unescape(insights_title)
                
                # Check for title directly in insights
                if not insights_title and "title" in insights and insights["title"]:
                    insights_title = insights["title"]
                    if isinstance(insights_title, str):
                        insights_title = fix_text(insights_title)
                        insights_title = html.unescape(insights_title)
                
                # Check for title in media_map_data
                if not insights_title and "media_map_data" in insights:
                    for media_key, media_data in insights["media_map_data"].items():
                        if "title" in media_data and media_data["title"]:
                            insights_title = media_data["title"]
                            if isinstance(insights_title, str):
                                insights_title = fix_text(insights_title)
                                insights_title = html.unescape(insights_title)
                            break  # Use the first media item with a title

            # Use the longer or non-empty title between post data and insights
            if post_title and insights_title:
                post_entry["tt"] = post_title if len(post_title) >= len(insights_title) else insights_title
            elif post_title:
                post_entry["tt"] = post_title
            elif insights_title:
                post_entry["tt"] = insights_title

            simplified_data[post_entry["t"]] = post_entry

        # Sort by timestamp (newest first)
        return dict(sorted(simplified_data.items(), key=lambda x: x[0], reverse=True))

    def process_json_strings(self, data):
        """
        Recursively process all string values in JSON data to fix encoding issues.
        """
        if isinstance(data, dict):
            return {k: self.process_json_strings(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.process_json_strings(item) for item in data]
        elif isinstance(data, str):
            # Apply all string fixes
            # Use ftfy to fix text encoding issues
            fixed = fix_text(data)
            # Still apply HTML unescaping after fixing encoding
            fixed = html.unescape(fixed)
            return fixed
        else:
            return data

    def load_all_data(self):
        """
        Load all data and return a comprehensive data package.

        Returns:
            dict: Data package containing all processed data
        """
        profile_info = self.load_profile_data()
        location_info = self.load_location_data()
        posts_data = self.extract_relevant_data()
        
        # Process all string values to fix encoding issues
        profile_info = self.process_json_strings(profile_info)
        location_info = self.process_json_strings(location_info)
        posts_data = self.process_json_strings(posts_data)

        # Get date range for display
        if posts_data:
            keys = list(posts_data.keys())
            first_key = keys[0]  # Newest post
            last_key = keys[-1]  # Oldest post

            # Format timestamps
            newest_post_date = datetime.utcfromtimestamp(int(first_key)).strftime(
                "%B %Y"
            )
            oldest_post_date = datetime.utcfromtimestamp(int(last_key)).strftime(
                "%B %Y"
            )

            date_range = {
                "newest": newest_post_date,
                "oldest": oldest_post_date,
                "range": f"{oldest_post_date} - {newest_post_date}",
            }
        else:
            date_range = {"newest": "Unknown", "oldest": "Unknown", "range": "Unknown"}

        return {
            "profile": profile_info,
            "location": location_info,
            "posts": posts_data,
            "date_range": date_range,
            "post_count": len(posts_data),
        }
