# memento_mori/cli.py

import os
import argparse
import multiprocessing
from pathlib import Path
import traceback
import sys

from memento_mori.extractor import InstagramArchiveExtractor
from memento_mori.loader import InstagramDataLoader
from memento_mori.media import InstagramMediaProcessor
from memento_mori.generator import InstagramSiteGenerator


def main():
    """Main entry point for the Memento Mori CLI."""
    parser = argparse.ArgumentParser(
        description="Transform Instagram data export into a viewer."
    )

    parser.add_argument(
        "--input",
        type=str,
        help="Path to Instagram data (ZIP or folder). If not specified, auto-detection will be used.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="./output",
        help="Output directory for generated website [default: ./output]",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=0,
        help="Number of parallel processing threads [default: auto]",
    )
    parser.add_argument(
        "--search-dir",
        type=str,
        default=".",
        help="Directory to search for Instagram exports when auto-detecting [default: current directory]",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=70,
        help="WebP conversion quality (1-100) [default: 70]",
    )
    parser.add_argument(
        "--max-dimension",
        type=int,
        default=1920,
        help="Maximum dimension for images in pixels [default: 1920]",
    )
    parser.add_argument(
        "--thumbnail-size",
        type=str,
        default="292x292",
        help="Size of thumbnails [default: 292x292]",
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Disable auto-detection (requires --input to be specified)",
    )
    parser.add_argument(
        "--gtag-id",
        type=str,
        help="Google Analytics tag ID (e.g., 'G-DX1ZWTC9NZ') to add tracking to the generated site",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    args = parser.parse_args()

    # Set defaults for threads if not specified
    if args.threads <= 0:
        args.threads = max(1, multiprocessing.cpu_count() - 1)

    # Parse thumbnail size
    try:
        if "x" in args.thumbnail_size:
            width, height = map(int, args.thumbnail_size.lower().split("x"))
            thumbnail_size = (width, height)
        else:
            size = int(args.thumbnail_size)
            thumbnail_size = (size, size)
    except ValueError:
        print(f"Invalid thumbnail size: {args.thumbnail_size}, using default 292x292")
        thumbnail_size = (292, 292)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extractor with input path if specified
    extractor = InstagramArchiveExtractor(input_path=args.input)

    # Handle input selection
    # If input is explicitly provided, use that
    if args.input:
        print(f"Using specified input: {args.input}")
    # If auto-detect is not disabled, try to find an export
    elif not args.no_auto_detect:
        print(f"Auto-detecting Instagram archive in {args.search_dir}...")
        detected_archive = extractor.auto_detect_archive(search_dir=args.search_dir)
        if not detected_archive:
            print(
                "No Instagram archive detected. Please specify an input file with --input."
            )
            return 1
        print(f"Detected archive: {detected_archive}")
    # If no input and auto-detect disabled, raise error
    else:
        print("Error: No input specified and auto-detection is disabled.")
        print("Please provide an input path with --input.")
        return 1

    try:
        # Extract archive
        print("\n📦 EXTRACTING ARCHIVE")
        print(f"   Source: {extractor.input_path}")
        extraction_dir = extractor.extract()
        print(f"   Extracted to: {extraction_dir}")

        # Get file mapper from extractor
        file_mapper = extractor.file_mapper

        # Initialize loader with the same file mapper
        print("\n📋 LOADING DATA")
        loader = InstagramDataLoader(extraction_dir, file_mapper, verbose=args.verbose)

        # Load and process data
        data = loader.load_all_data()
        
        if args.verbose:
            print("\n🔍 VERBOSE: Data Loading Details")
            print(f"   Profile data found: {'Yes' if loader.profile_data else 'No'}")
            print(f"   Location data found: {'Yes' if loader.location_data else 'No'}")
            print(f"   Posts data found: {'Yes' if loader.posts_data else 'No'}")
            print(f"   Insights data found: {'Yes' if loader.insights_data else 'No'}")
            print(f"   Combined data entries: {len(loader.combined_data) if loader.combined_data else 0}")
            
            # Show file paths that were found
            print("\n   File paths found:")
            for file_type, file_path in file_mapper.file_map.items():
                if isinstance(file_path, list):
                    print(f"      {file_type}: {len(file_path)} files")
                    if args.verbose:
                        for i, path in enumerate(file_path[:3]):  # Show first 3 only
                            print(f"         - {path}")
                        if len(file_path) > 3:
                            print(f"         - ... and {len(file_path)-3} more")
                else:
                    print(f"      {file_type}: {file_path}")
        
        print(f"   Found {data['post_count']} posts from {data['profile']['username']}")

        # Process media files
        print(f"\n🖼️  PROCESSING MEDIA")
        print(f"   Using {args.threads} threads, quality {args.quality}, max dimension {args.max_dimension}...")
        media_processor = InstagramMediaProcessor(
            extraction_dir, output_dir, thread_count=args.threads,
            quality=args.quality, max_dimension=args.max_dimension
        )
        media_result = media_processor.process_media_files(
            data["posts"], data["profile"]["profile_picture"], data.get("stories", {})
        )

        # Update data with shortened filenames
        data["posts"] = media_result["updated_post_data"]
        data["profile"]["profile_picture"] = media_result["shortened_profile"]
        
        # Update stories data if it exists
        if "stories" in data and media_result.get("updated_stories_data"):
            data["stories"] = media_result["updated_stories_data"]

        # Generate website with the loaded data
        print("\n🌐 GENERATING WEBSITE")
        generator = InstagramSiteGenerator(data, output_dir, gtag_id=args.gtag_id)
        success = generator.generate()

        if success:
            stats = media_result["stats"]
            print("\n✅ PROCESS COMPLETE")
            print(f"   Website generated at: {output_dir}")
            print(f"   Posts processed: {data['post_count']}")
            print(f"   Media files processed: {stats['thumbnail_count'] + stats['webp_count']}")
            print(f"   Space saved: {stats['space_saved_mb']:.2f} MB ({stats['percentage_saved']:.1f}%)")
            print(f"   Fixed file extensions: {stats['extension_fixes']}")
            return 0
        else:
            print("\n❌ ERROR: Failed to generate website.")
            return 1

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        if args.verbose:
            print("\n🔍 VERBOSE: Exception traceback")
            traceback.print_exc(file=sys.stdout)
        return 1


if __name__ == "__main__":
    exit(main())
