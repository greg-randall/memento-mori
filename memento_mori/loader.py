# memento_mori/loader.py
import json
from datetime import datetime
import html


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
                    # Ensure proper Unicode handling when loading JSON
                    posts_data = json.load(f, strict=False)
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
                insights_raw = json.load(f)

            # Index insights by timestamp
            insights_indexed = {}
            for insight in insights_raw.get("organic_insights_posts", []):
                if (
                    "media_map_data" in insight
                    and "Media Thumbnail" in insight["media_map_data"]
                ):
                    timestamp = insight["media_map_data"]["Media Thumbnail"][
                        "creation_timestamp"
                    ]
                    insights_indexed[timestamp] = insight

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

        for post in self.posts_data:
            try:
                # Get the timestamp from the first media item
                timestamp = post["media"][0]["creation_timestamp"]

                # Find associated insights
                insight = self.insights_data.get(timestamp)

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
            # Initialize a new post entry
            post_entry = {
                "post_index": index,
                "media": [],
                "creation_timestamp_unix": "",
                "creation_timestamp_readable": "",
                "title": "",
                "Impressions": "",
                "Likes": "",
                "Comments": "",
            }

            # Extract post-level data
            if "post_data" in item:
                if "creation_timestamp" in item["post_data"]:
                    post_entry["creation_timestamp_unix"] = item["post_data"][
                        "creation_timestamp"
                    ]
                elif (
                    "media" in item["post_data"]
                    and len(item["post_data"]["media"]) > 0
                    and "creation_timestamp" in item["post_data"]["media"][0]
                ):
                    # Fallback to first media item timestamp if post timestamp not available
                    post_entry["creation_timestamp_unix"] = item["post_data"]["media"][
                        0
                    ]["creation_timestamp"]

                post_entry["creation_timestamp_readable"] = datetime.utcfromtimestamp(
                    post_entry["creation_timestamp_unix"]
                ).strftime("%B %d, %Y at %I:%M %p")

                if "title" in item["post_data"]:
                    # First decode any Unicode escape sequences, then unescape HTML entities
                    title = item["post_data"]["title"]
                    # Handle the case where title might be a string with Unicode escape sequences
                    if isinstance(title, str):
                        # The JSON loader should have already decoded Unicode escapes,
                        # but we'll ensure proper handling of any remaining issues
                        title = html.unescape(title)
                    post_entry["title"] = title

                # Extract media URIs
                if "media" in item["post_data"]:
                    for media in item["post_data"]["media"]:
                        if "uri" in media:
                            post_entry["media"].append(media["uri"])
                        else:
                            post_entry["media"].append("")

            # Get insights data if available
            if (
                "insights" in item
                and item["insights"]
                and "string_map_data" in item["insights"]
            ):
                insights = item["insights"]["string_map_data"]

                # Extract specific metrics and ensure they're integers or blank
                if "Impressions" in insights:
                    impressions = insights["Impressions"].get("value", "")
                    # Validate and convert to integer if numeric, otherwise leave blank
                    post_entry["Impressions"] = (
                        int(impressions)
                        if impressions and impressions.isdigit()
                        else ""
                    )

                if "Likes" in insights:
                    likes = insights["Likes"].get("value", "")
                    # Validate and convert to integer if numeric, otherwise leave blank
                    post_entry["Likes"] = (
                        int(likes) if likes and likes.isdigit() else ""
                    )

                if "Comments" in insights:
                    comments = insights["Comments"].get("value", "")
                    # Validate and convert to integer if numeric, otherwise leave blank
                    post_entry["Comments"] = (
                        int(comments) if comments and comments.isdigit() else ""
                    )

            simplified_data[post_entry["creation_timestamp_unix"]] = post_entry

        # Sort by timestamp (newest first)
        return dict(sorted(simplified_data.items(), key=lambda x: x[0], reverse=True))

    def load_all_data(self):
        """
        Load all data and return a comprehensive data package.

        Returns:
            dict: Data package containing all processed data
        """
        profile_info = self.load_profile_data()
        location_info = self.load_location_data()
        posts_data = self.extract_relevant_data()

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
