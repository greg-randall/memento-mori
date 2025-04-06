# memento_mori/generator.py
import os
import json
import shutil
import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import re
import hashlib


class InstagramSiteGenerator:
    """
    Class for generating the static website from processed Instagram data.

    This class handles:
    - Creating HTML using templates
    - Copying static assets (CSS, JS)
    - Verifying the completeness of the output
    """

    def __init__(self, data_package, output_dir, template_dir=None, static_dir=None):
        """Initialize the generator with data and path options."""
        self.data_package = data_package
        self.output_dir = Path(output_dir)

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

    def _generate_html(self):
        """Generate HTML using templates."""
        # Generate the grid HTML
        grid_html = self._render_grid()

        # Extract data for the main template
        profile_info = self.data_package["profile"]
        location_info = self.data_package.get("location", {"location": "Unknown"})
        date_range = self.data_package["date_range"]["range"]
        post_count = self.data_package["post_count"]

        # Current date for footer
        generation_date = datetime.datetime.now().strftime("%Y-%m-%d")

        # Render the main template
        template = self.jinja_env.get_template("index.html")
        html_content = template.render(
            username=profile_info["username"],
            profile_picture=profile_info["profile_picture"],
            date_range=date_range,
            post_count=post_count,
            grid_html=grid_html,
            post_data_json=json.dumps(self.data_package["posts"]),
            generation_date=generation_date,
        )

        # Write HTML file
        with open(self.output_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Generated HTML file: {self.output_dir / 'index.html'}")

    def _render_grid(self):
        """Render the grid HTML using the grid.html template."""
        posts_data = self.data_package["posts"]
        lazy_after = 30  # Start lazy loading after this many posts

        # Prepare data for the grid template
        grid_posts = []
        for i, (timestamp, post) in enumerate(posts_data.items()):
            # Determine which media to use for the grid thumbnail
            display_media = self._get_display_media(post, i >= lazy_after)

            grid_posts.append(
                {
                    "index": post["post_index"],
                    "display_media": display_media["url"],
                    "is_video": display_media["is_video"],
                    "media_count": len(post["media"]),
                    "likes": post.get("Likes", ""),
                    "lazy_load": ' loading="lazy"' if i >= lazy_after else "",
                }
            )

        # Render grid template
        grid_template = self.jinja_env.get_template("grid.html")
        return grid_template.render(posts=grid_posts)

    def _get_display_media(self, post, use_lazy_loading=False):
        """Determine which media to use for the grid thumbnail."""
        result = {"url": "", "is_video": False}

        if not post["media"] or len(post["media"]) == 0:
            return result

        first_media = post["media"][0]
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
                for media_item in post["media"]:
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
