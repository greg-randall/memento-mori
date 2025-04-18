# memento_mori/loader.py
import json
import re
import os
from datetime import datetime
import html
from ftfy import fix_text
from pathlib import Path


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

    def __init__(self, extraction_dir, file_mapper=None, verbose=False):
        """
        Initialize the loader with the path to the extracted data.

        Args:
            extraction_dir (str): Path to the extracted Instagram data
            file_mapper (InstagramFileMapper, optional): File mapper from extractor
            verbose (bool): Whether to print verbose debug information
        """
        self.extraction_dir = extraction_dir
        self.file_mapper = file_mapper
        self.verbose = verbose

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
            return {"username": "Unknown", "profile_picture": "", "bio": ""}

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
                "bio": "",  # Initialize bio as empty string
                "website": ""  # Initialize website as empty string
            }
            
            # Extract bio if available
            if "Bio" in self.profile_data["profile_user"][0]["string_map_data"]:
                profile_info["bio"] = self.profile_data["profile_user"][0]["string_map_data"]["Bio"]["value"]
                if self.verbose:
                    print(f"Found bio: {profile_info['bio'][:30]}...")
            
            # Extract website if available
            if "Website" in self.profile_data["profile_user"][0]["string_map_data"]:
                profile_info["website"] = self.profile_data["profile_user"][0]["string_map_data"]["Website"]["value"]
                if self.verbose:
                    print(f"Found website: {profile_info['website']}")

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

        if self.verbose:
            print(f"Found {len(post_paths)} posts data file(s):")
            for i, path in enumerate(post_paths):
                print(f"  {i+1}. {path}")

        for posts_path in post_paths:
            try:
                if self.verbose:
                    print(f"Loading posts from: {posts_path}")
                
                with open(posts_path, "r", encoding="utf-8") as f:
                    # Read the file content first
                    file_content = f.read()
                    
                    if self.verbose:
                        print(f"  File size: {len(file_content)} bytes")
                    
                    # Fix encoding issues with ftfy
                    file_content = fix_text(file_content)
                    
                    # Parse the modified content
                    posts_data = json.loads(file_content, strict=False)
                    
                    # Check if posts_data is a list (expected format)
                    if isinstance(posts_data, list):
                        if self.verbose:
                            print(f"  Found {len(posts_data)} posts in list format")
                        all_posts.extend(posts_data)
                    elif isinstance(posts_data, dict):
                        # Some exports might have posts as a dictionary
                        if self.verbose:
                            print(f"  Found posts in dictionary format")
                            print(f"  Dictionary keys: {', '.join(list(posts_data.keys())[:5])}...")
                        
                        # Try to extract a list from it
                        if "posts" in posts_data and isinstance(posts_data["posts"], list):
                            if self.verbose:
                                print(f"  Found {len(posts_data['posts'])} posts in 'posts' key")
                            all_posts.extend(posts_data["posts"])
                        else:
                            # Add the dict as a single item if we can't extract a list
                            if self.verbose:
                                print(f"  No 'posts' list found, adding dictionary as a single item")
                            all_posts.append(posts_data)
                    else:
                        print(f"Warning: Unexpected posts data format in {posts_path}")
                        if self.verbose:
                            print(f"  Data type: {type(posts_data)}")
            except Exception as e:
                print(f"Error loading posts data from {posts_path}: {str(e)}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()

        if not all_posts:
            print("Warning: No posts data could be loaded from any file")
        elif self.verbose:
            print(f"Successfully loaded {len(all_posts)} posts in total")
            
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
            # Initialize as empty dict, not None
            self.insights_data = {}
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
            if self.verbose:
                print("No posts data yet, loading posts data")
            self.load_posts_data()

        if self.insights_data is None:
            if self.verbose:
                print("No insights data yet, loading insights data")
            self.load_insights_data()

        # Ensure insights_data is a dictionary
        if not isinstance(self.insights_data, dict):
            if self.verbose:
                print("Warning: insights_data is not a dictionary, initializing as empty")
            self.insights_data = {}

        if self.verbose:
            print(f"Combining {len(self.posts_data) if self.posts_data else 0} posts with {len(self.insights_data)} insights entries")

        combined = []
        
        # Create a mapping of timestamps to insights for faster lookup
        insights_map = {}
        for timestamp, insight in self.insights_data.items():
            insights_map[str(timestamp)] = insight

        if not self.posts_data:
            if self.verbose:
                print("Warning: No posts data to combine")
            self.combined_data = []
            return []

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
                
                if self.verbose and not timestamp:
                    print(f"Warning: Post without timestamp")
                    print(f"  Post keys: {', '.join(list(post.keys())[:5])}...")
                    if "media" in post:
                        print(f"  Media items: {len(post['media'])}")
                        if len(post["media"]) > 0:
                            print(f"  First media keys: {', '.join(list(post['media'][0].keys())[:5])}...")
                
            except (IndexError, KeyError) as e:
                print(f"Error processing post: {str(e)}")
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                    print(f"  Post keys: {', '.join(list(post.keys())[:5])}...")
                # Add post without insights
                combined.append({"post_data": post, "insights": None})

        if self.verbose:
            print(f"Created {len(combined)} combined entries")
            
        self.combined_data = combined
        return combined

    def extract_relevant_data(self):
        """
        Extract relevant data from the combined posts and insights data.

        Returns:
            dict: Simplified data structure with relevant information
        """
        if self.combined_data is None:
            if self.verbose:
                print("No combined data yet, calling combine_data()")
            self.combine_data()
            
        # Check if combined_data is still None or empty after trying to combine
        if not self.combined_data:
            print("Warning: No post data found or could not be processed.")
            if self.verbose:
                print("combined_data is None or empty after combine_data() call")
                print(f"posts_data: {type(self.posts_data)}, length: {len(self.posts_data) if self.posts_data else 0}")
                print(f"insights_data: {type(self.insights_data)}, length: {len(self.insights_data) if self.insights_data else 0}")
            return {}

        if self.verbose:
            print(f"Processing {len(self.combined_data)} combined data entries")

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
                            if self.verbose:
                                print(f"Warning: Media item without URI at post index {index}")
                                print(f"  Media keys: {', '.join(list(media.keys())[:5])}...")
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

            # Only add posts with valid timestamps
            if post_entry["t"]:
                simplified_data[post_entry["t"]] = post_entry
            elif self.verbose:
                print(f"Skipping post at index {index} due to missing timestamp")

        if self.verbose:
            print(f"Extracted {len(simplified_data)} posts with valid timestamps")
            
        # Sort by timestamp (newest first)
        sorted_data = dict(sorted(simplified_data.items(), key=lambda x: x[0], reverse=True))
        
        if self.verbose and sorted_data:
            print(f"Posts date range: {datetime.utcfromtimestamp(int(list(sorted_data.keys())[-1])).strftime('%Y-%m-%d')} to {datetime.utcfromtimestamp(int(list(sorted_data.keys())[0])).strftime('%Y-%m-%d')}")
            
        return sorted_data

    def load_followers_data(self):
        """
        Load followers data and count the number of followers.

        Returns:
            int: Number of followers
        """
        followers_path = self.file_mapper.get_file_path("followers")
        if not followers_path:
            if self.verbose:
                print("Followers data not found")
            return 0

        try:
            with open(followers_path, "r", encoding="utf-8") as f:
                file_content = f.read()
                # Fix encoding issues
                file_content = fix_text(file_content)
                followers_data = json.loads(file_content, strict=False)

            # Count the number of followers
            follower_count = len(followers_data)
            
            if self.verbose:
                print(f"Found {follower_count} followers")
                
            return follower_count
        except Exception as e:
            print(f"Error loading followers data: {str(e)}")
            return 0
            
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

    def load_stories_data(self):
        """
        Load stories data from stories JSON files.

        Returns:
            dict: Processed stories data
        """
        stories_path = self.file_mapper.get_file_path("stories")
        if not stories_path:
            if self.verbose:
                print("\n🔍 STORIES DATA SEARCH")
                print("   No stories file found in standard locations")
                print("   Checking all patterns for stories files:")
                for pattern in self.file_mapper.FILE_PATTERNS["stories"]:
                    print(f"   - Searching with pattern: {pattern}")
                    matches = list(Path(self.file_mapper.base_dir).glob(pattern))
                    if matches:
                        print(f"     Found {len(matches)} matches:")
                        for match in matches[:3]:  # Show first 3
                            print(f"     • {match}")
                        if len(matches) > 3:
                            print(f"     • ... and {len(matches)-3} more")
                    else:
                        print(f"     No matches found")
                
                # Try a more aggressive search
                print("\n   Performing deep search for any files containing 'stories':")
                for root, dirs, files in os.walk(self.file_mapper.base_dir):
                    for file in files:
                        if 'stories' in file.lower() and file.endswith('.json'):
                            print(f"     • Found potential stories file: {os.path.join(root, file)}")
            return {}

        try:
            if self.verbose:
                print(f"\n🔍 STORIES DATA LOADING")
                print(f"   Found stories file: {stories_path}")
                file_size = os.path.getsize(stories_path)
                print(f"   File size: {file_size} bytes")
            
            with open(stories_path, "r", encoding="utf-8") as f:
                file_content = f.read()
                # Fix encoding issues
                file_content = fix_text(file_content)
                
                if self.verbose:
                    print(f"   Parsing JSON content...")
                
                stories_data = json.loads(file_content, strict=False)
                
                if self.verbose:
                    print(f"   JSON parsed successfully")
                    if isinstance(stories_data, dict):
                        print(f"   Data structure: Dictionary with {len(stories_data)} keys")
                        print(f"   Top-level keys: {', '.join(list(stories_data.keys())[:5])}")
                    elif isinstance(stories_data, list):
                        print(f"   Data structure: List with {len(stories_data)} items")
                    else:
                        print(f"   Data structure: {type(stories_data)}")

            # Process stories data similar to posts
            simplified_stories = {}
            
            # Handle different possible structures
            stories_list = []
            
            if self.verbose:
                print(f"\n   Extracting stories list from data structure...")
            
            if isinstance(stories_data, list):
                stories_list = stories_data
                if self.verbose:
                    print(f"   Using top-level list with {len(stories_list)} items")
            elif isinstance(stories_data, dict):
                # Try different possible keys where stories might be stored
                possible_keys = ["stories", "story_activities", "story_media", "items"]
                for key in possible_keys:
                    if key in stories_data and isinstance(stories_data[key], list):
                        stories_list = stories_data[key]
                        if self.verbose:
                            print(f"   Found stories in '{key}' key: {len(stories_list)} items")
                        break
                
                if not stories_list and self.verbose:
                    print(f"   Could not find stories list in dictionary keys")
                    print(f"   Available keys: {', '.join(list(stories_data.keys()))}")
            
            if self.verbose:
                print(f"\n   Processing {len(stories_list)} stories...")
            
            for index, story in enumerate(stories_list):
                # Initialize a new story entry with shortened keys
                story_entry = {
                    "i": index,  # story_index
                    "m": [],     # media
                    "t": "",     # creation_timestamp_unix
                    "d": "",     # creation_timestamp_readable
                    "tt": "",    # title/caption
                }
                
                if self.verbose and index < 3:  # Only show details for first 3 stories
                    print(f"\n   Story #{index+1}:")
                    if isinstance(story, dict):
                        print(f"   Keys: {', '.join(list(story.keys())[:10])}")
                
                # Extract timestamp
                timestamp_found = False
                if isinstance(story, dict):
                    # Try different possible timestamp fields
                    timestamp_fields = ["creation_timestamp", "taken_at", "timestamp"]
                    for field in timestamp_fields:
                        if field in story and story[field]:
                            story_entry["t"] = int(story[field])
                            timestamp_found = True
                            if self.verbose and index < 3:
                                print(f"   Timestamp found in '{field}': {story_entry['t']}")
                            break
                    
                    # Try media items if no timestamp at story level
                    if not timestamp_found and "media" in story and isinstance(story["media"], list) and len(story["media"]) > 0:
                        for media_item in story["media"]:
                            if isinstance(media_item, dict):
                                for field in timestamp_fields:
                                    if field in media_item and media_item[field]:
                                        story_entry["t"] = int(media_item[field])
                                        timestamp_found = True
                                        if self.verbose and index < 3:
                                            print(f"   Timestamp found in media item '{field}': {story_entry['t']}")
                                        break
                                if timestamp_found:
                                    break
                
                # Format date if timestamp found
                if story_entry["t"]:
                    story_entry["d"] = datetime.utcfromtimestamp(
                        int(story_entry["t"])
                    ).strftime("%B %d, %Y at %I:%M %p")
                    if self.verbose and index < 3:
                        print(f"   Formatted date: {story_entry['d']}")
                
                # Extract caption/title
                caption_found = False
                if isinstance(story, dict):
                    # Try different possible caption fields
                    caption_fields = ["caption", "title", "text"]
                    for field in caption_fields:
                        if field in story and story[field]:
                            story_entry["tt"] = story[field]
                            caption_found = True
                            if self.verbose and index < 3:
                                print(f"   Caption found in '{field}': {story_entry['tt'][:30]}...")
                            break
                    
                    # Try string_map_data if no caption found directly
                    if not caption_found and "string_map_data" in story and isinstance(story["string_map_data"], dict):
                        string_map = story["string_map_data"]
                        caption_keys = ["Caption", "Text", "Story Text"]
                        for key in caption_keys:
                            if key in string_map and isinstance(string_map[key], dict) and "value" in string_map[key]:
                                story_entry["tt"] = string_map[key]["value"]
                                caption_found = True
                                if self.verbose and index < 3:
                                    print(f"   Caption found in string_map_data['{key}']: {story_entry['tt'][:30]}...")
                                break
                
                # Extract media URIs
                media_found = False
                if isinstance(story, dict):
                    # Try direct URI field
                    if "uri" in story and story["uri"]:
                        story_entry["m"].append(story["uri"])
                        media_found = True
                        if self.verbose and index < 3:
                            print(f"   Media found directly in 'uri': {story_entry['m'][0]}")
                    
                    # Try media list
                    if "media" in story and isinstance(story["media"], list):
                        for media_item in story["media"]:
                            if isinstance(media_item, dict) and "uri" in media_item and media_item["uri"]:
                                story_entry["m"].append(media_item["uri"])
                                media_found = True
                                if self.verbose and index < 3 and len(story_entry["m"]) <= 3:
                                    print(f"   Media found in media list: {media_item['uri']}")
                    
                    # Try media_map_data
                    if not media_found and "media_map_data" in story and isinstance(story["media_map_data"], dict):
                        for key, media_item in story["media_map_data"].items():
                            if isinstance(media_item, dict) and "uri" in media_item and media_item["uri"]:
                                story_entry["m"].append(media_item["uri"])
                                media_found = True
                                if self.verbose and index < 3 and len(story_entry["m"]) <= 3:
                                    print(f"   Media found in media_map_data['{key}']: {media_item['uri']}")
                
                # Only add stories with valid timestamps and media
                if story_entry["t"] and story_entry["m"]:
                    simplified_stories[str(story_entry["t"])] = story_entry
                    if self.verbose and index < 3:
                        print(f"   ✓ Story added with timestamp {story_entry['t']} and {len(story_entry['m'])} media items")
                elif self.verbose and index < 3:
                    if not story_entry["t"]:
                        print(f"   ✗ Story skipped: No timestamp found")
                    if not story_entry["m"]:
                        print(f"   ✗ Story skipped: No media found")
            
            if self.verbose:
                print(f"\n   Extracted {len(simplified_stories)} valid stories from {len(stories_list)} total")
            
            # Sort by timestamp (newest first)
            sorted_stories = dict(sorted(simplified_stories.items(), key=lambda x: int(x[0]), reverse=True))
            
            if self.verbose and sorted_stories:
                newest = datetime.utcfromtimestamp(int(list(sorted_stories.keys())[0])).strftime('%Y-%m-%d')
                oldest = datetime.utcfromtimestamp(int(list(sorted_stories.keys())[-1])).strftime('%Y-%m-%d')
                print(f"   Stories date range: {oldest} to {newest}")
            
            return sorted_stories
            
        except Exception as e:
            print(f"Error loading stories data: {str(e)}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return {}

    def load_all_data(self):
        """
        Load all data and return a comprehensive data package.

        Returns:
            dict: Data package containing all processed data
        """
        profile_info = self.load_profile_data()
        location_info = self.load_location_data()
        posts_data = self.extract_relevant_data()
        stories_data = self.load_stories_data()
        follower_count = self.load_followers_data()
        
        # Add follower count to profile info
        profile_info["follower_count"] = follower_count
        
        # Process all string values to fix encoding issues
        profile_info = self.process_json_strings(profile_info)
        location_info = self.process_json_strings(location_info)
        posts_data = self.process_json_strings(posts_data)
        stories_data = self.process_json_strings(stories_data)

        # Get date range for display
        if posts_data and isinstance(posts_data, dict) and len(posts_data) > 0:
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
            # If no posts data, create an empty dict to avoid NoneType errors
            if not isinstance(posts_data, dict):
                posts_data = {}

        return {
            "profile": profile_info,
            "location": location_info,
            "posts": posts_data,
            "stories": stories_data,
            "date_range": date_range,
            "post_count": len(posts_data),
            "story_count": len(stories_data),
        }
