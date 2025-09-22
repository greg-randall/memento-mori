# memento_mori/generator.py
import os
import json
import shutil
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
import re
import hashlib
import base64


class InstagramSiteGenerator:
    """
    Class for generating the static website from processed Instagram data.

    This class handles:
    - Creating HTML using templates
    - Copying static assets (CSS, JS)
    - Verifying the completeness of the output
    """

    def __init__(self, data_package, output_dir, template_dir=None, static_dir=None, gtag_id=None):
        """Initialize the generator with data and path options."""
        self.data_package = data_package
        self.output_dir = Path(output_dir)
        self.gtag_id = gtag_id  # Store the Google tag ID

        # Find template directory
        if template_dir is None:
            # Try to find templates relative to this file or common locations
            module_dir = Path(__file__).parent
            template_dir = module_dir / "templates"

            if not template_dir.exists():
                for path in [
                    Path("templates"),
                    Path("./templates"),
                    Path("../templates"),
                ]:
                    if path.exists():
                        template_dir = path
                        break

        # Find static directory
        if static_dir is None:
            module_dir = Path(__file__).parent
            static_dir = module_dir / "static"

            if not static_dir.exists():
                for path in [Path("static"), Path("./static"), Path("../static")]:
                    if path.exists():
                        static_dir = path
                        break

        self.template_dir = Path(template_dir)
        self.static_dir = Path(static_dir)

        print(f"Using template directory: {self.template_dir}")
        print(f"Using static directory: {self.static_dir}")

        # Set up Jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)), autoescape=True
        )

    def generate(self):
        """Generate the complete static website and verify output."""
        try:
            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Create CSS and JS directories in output
            (self.output_dir / "css").mkdir(exist_ok=True)
            (self.output_dir / "js").mkdir(exist_ok=True)

            # Copy static assets
            self._copy_static_assets()

            # Generate HTML
            self._generate_html()
            
            # Generate stories HTML if we have stories data
            if "stories" in self.data_package and self.data_package["stories"]:
                self._generate_stories_html()

            print(f"Website successfully generated at {self.output_dir}")
            return True

        except Exception as e:
            print(f"Error generating website: {str(e)}")
            return False

    def _copy_static_assets(self):
        """Copy CSS and JS files to the output directory."""
        # Copy CSS
        css_dir = self.static_dir / "css"
        if css_dir.exists():
            for css_file in css_dir.glob("*.css"):
                shutil.copy2(css_file, self.output_dir / "css" / css_file.name)
                print(f"Copied CSS: {css_file.name}")

        # Copy JS
        js_dir = self.static_dir / "js"
        if js_dir.exists():
            for js_file in js_dir.glob("*.js"):
                shutil.copy2(js_file, self.output_dir / "js" / js_file.name)
                print(f"Copied JS: {js_file.name}")
            
            # Ensure stories.js exists, create it if not
            stories_js = js_dir / "stories.js"
            if not stories_js.exists():
                # Create a minimal stories.js file if it doesn't exist
                with open(stories_js, "w") as f:
                    f.write("// Stories viewer functionality\n")
                print(f"Created placeholder: stories.js")
            
            # Copy stories.js to output
            shutil.copy2(stories_js, self.output_dir / "js" / "stories.js")
            print(f"Copied JS: stories.js")

    def _generate_html(self):
        """Generate HTML using templates."""
        # Generate the grid HTML
        grid_html = self._render_grid()

        # Extract data for the main template
        profile_info = self.data_package["profile"]
        location_info = self.data_package.get("location", {"location": "Unknown"})
        date_range = self.data_package["date_range"]["range"]
        post_count = self.data_package["post_count"]
        story_count = self.data_package.get("story_count", 0)
        
        # Get profile picture path and check for WebP version
        profile_picture = profile_info["profile_picture"]
        
        # Check if we have a WebP version of the profile picture
        if profile_picture:
            webp_path = re.sub(r"\.(jpg|jpeg|png|gif)$", ".webp", profile_picture, flags=re.I)
            if os.path.exists(os.path.join(self.output_dir, webp_path)):
                profile_picture = webp_path

        # Current date for footer
        generation_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Get stories data or empty dict if not available
        stories_data = self.data_package.get("stories", {})

        # Render the main template
        template = self.jinja_env.get_template("index.html")
        html_content = template.render(
            username=profile_info["username"],
            profile_picture=profile_picture,
            bio=profile_info.get("bio", ""),  # Pass bio to template
            profile=profile_info,  # Pass the entire profile object
            date_range=date_range,
            post_count=post_count,
            story_count=story_count,
            has_stories=story_count > 0,  # Flag to show stories link
            grid_html=grid_html,
            post_data_json=json.dumps(self.data_package["posts"], ensure_ascii=False),
            stories_data_json=json.dumps(stories_data, ensure_ascii=False),  # Add stories data
            generation_date=generation_date,
            gtag_id=self.gtag_id,  # Add Google tag ID
        )

        # Write HTML file
        with open(self.output_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Generated HTML file: {self.output_dir / 'index.html'}")

    def _render_grid(self):
        """Render the grid HTML using the grid.html template."""
        posts_data = self.data_package["posts"]
        lazy_after = 30  # Start lazy loading after this many posts

        # Check if posts_data is valid
        if not posts_data or not isinstance(posts_data, dict):
            print("Warning: No valid posts data found for grid rendering")
            return ""

        # Prepare data for the grid template
        grid_posts = []
        for i, (timestamp, post) in enumerate(posts_data.items()):
            # Determine which media to use for the grid thumbnail
            display_media = self._get_display_media(post, i >= lazy_after)

            grid_posts.append(
                {
                    "index": post["i"],
                    "display_media": display_media["url"],
                    "is_video": display_media["is_video"],
                    "media_count": len(post["m"]),
                    "likes": post.get("l", ""),
                    "lazy_load": Markup(' loading="lazy"') if i >= lazy_after else "",
                }
            )

        # Render grid template
        grid_template = self.jinja_env.get_template("grid.html")
        return grid_template.render(posts=grid_posts)

    def _get_display_media(self, post, use_lazy_loading=False):
        """Determine which media to use for the grid thumbnail."""
        result = {"url": "", "is_video": False}

        if not post["m"] or len(post["m"]) == 0:
            return result

        first_media = post["m"][0]
        result["url"] = first_media

        # Check if first media is a video
        result["is_video"] = bool(
            re.search(r"\.(mp4|mov|avi|webm)$", first_media, re.I)
            if first_media
            else False
        )

        # Check if we have a thumbnail for this media
        if first_media:
            thumb_filename = hashlib.md5(first_media.encode()).hexdigest() + ".webp"
            thumb_path = f"thumbnails/{thumb_filename}"

            if os.path.exists(os.path.join(self.output_dir, thumb_path)):
                # Use the thumbnail instead of the original
                result["url"] = thumb_path
            elif not result["is_video"]:
                # Check if we have a WebP version of the original image
                webp_path = re.sub(
                    r"\.(jpg|jpeg|png|gif)$", ".webp", first_media, flags=re.I
                )
                if os.path.exists(os.path.join(self.output_dir, webp_path)):
                    result["url"] = webp_path

            # If it's a video, look for a thumbnail among all media items
            if (
                result["is_video"] and result["url"] == first_media
            ):  # No thumbnail found yet
                for media_item in post["m"]:
                    if re.search(r"\.(jpg|jpeg|png|webp|gif)$", media_item, re.I):
                        # Check if we have a thumbnail for this image
                        img_thumb_filename = (
                            hashlib.md5(media_item.encode()).hexdigest() + ".webp"
                        )
                        img_thumb_path = f"thumbnails/{img_thumb_filename}"

                        if os.path.exists(
                            os.path.join(self.output_dir, img_thumb_path)
                        ):
                            result["url"] = img_thumb_path
                            break
                        else:
                            result["url"] = media_item
                            break

                # If no thumbnail found, use a SVG placeholder
                if result["url"] == first_media:
                    # Create a simple SVG with a play button
                    svg = (
                        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">'
                        '<rect width="400" height="400" fill="#333333"/>'
                        '<circle cx="200" cy="200" r="60" fill="#ffffff" fill-opacity="0.8"/>'
                        '<polygon points="180,160 180,240 240,200" fill="#333333"/>'
                        "</svg>"
                    )

                    # Encode the SVG properly for use in an img src attribute
                    result["url"] = (
                        "data:image/svg+xml;base64,"
                        + base64.b64encode(svg.encode()).decode()
                    )

        return result
    def _generate_stories_html(self):
        """Generate a separate HTML file for stories."""
        stories_data = self.data_package.get("stories", {})
        
        if not stories_data:
            print("No stories data found, skipping stories.html generation")
            return
        
        # Extract data for the stories template
        profile_info = self.data_package["profile"]
        date_range = self.data_package["date_range"]["range"]
        story_count = len(stories_data)
        post_count = self.data_package["post_count"]
        
        # Get profile picture path and check for WebP version
        profile_picture = profile_info["profile_picture"]
        
        # Check if we have a WebP version of the profile picture
        if profile_picture:
            webp_path = re.sub(r"\.(jpg|jpeg|png|gif)$", ".webp", profile_picture, flags=re.I)
            if os.path.exists(os.path.join(self.output_dir, webp_path)):
                profile_picture = webp_path

        # Current date for footer
        generation_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Prepare stories data for the template
        stories_list = []
        lazy_after = 30  # Start lazy loading after this many stories
        
        for i, (timestamp, story) in enumerate(stories_data.items()):
            # Check for story-specific thumbnail
            story_thumb = story.get("story_thumb", None)
            
            if story_thumb and os.path.exists(os.path.join(self.output_dir, story_thumb)):
                # Use the 9:16 story thumbnail
                media_url = story_thumb
            else:
                # Fall back to regular thumbnail or original media
                display_media = self._get_display_media(story, i >= lazy_after)
                media_url = display_media["url"]
            
            # Determine if it's a video
            is_video = bool(re.search(r"\.(mp4|mov|avi|webm)$", story["m"][0], re.I)) if story["m"] else False
            
            stories_list.append({
                "index": story["i"],
                "media": media_url,
                "is_video": is_video,
                "date": story.get("d", ""),
                "caption": story.get("tt", ""),
                "timestamp": timestamp,
                "lazy_load": Markup(' loading="lazy"') if i >= lazy_after else "",
                "original_media": story["m"][0] if story["m"] else "",  # Include original media path
            })
        
        # Render the stories template
        template = self.jinja_env.get_template("stories_page.html")
        html_content = template.render(
            username=profile_info["username"],
            profile_picture=profile_picture,
            bio=profile_info.get("bio", ""),
            profile=profile_info,
            date_range=date_range,
            post_count=post_count,
            story_count=story_count,
            stories=stories_list,
            stories_data_json=json.dumps(stories_data, ensure_ascii=False),
            generation_date=generation_date,
            gtag_id=self.gtag_id,
        )
        
        # Write HTML file
        with open(self.output_dir / "stories.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"Generated stories HTML file: {self.output_dir / 'stories.html'}")
