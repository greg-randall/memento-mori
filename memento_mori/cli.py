# memento_mori/cli.py

import os
import argparse
import multiprocessing
from pathlib import Path

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
        default=80,
        help="WebP conversion quality (1-100) [default: 80]",
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
        print("Extracting archive...")
        extraction_dir = extractor.extract()

        # Get file mapper from extractor
        file_mapper = extractor.file_mapper

        # Initialize loader with the same file mapper
        print("Loading Instagram data...")
        loader = InstagramDataLoader(extraction_dir, file_mapper)

        # Load and process data
        data = loader.load_all_data()

        # Process media files
        print(
            f"Processing media with {args.threads} threads, quality {args.quality}..."
        )
        media_processor = InstagramMediaProcessor(
            extraction_dir, output_dir, thread_count=args.threads
        )
        media_processor.process_media_files(
            data["posts"], data["profile"]["profile_picture"]
        )

        # Generate website with the loaded data
        print("Generating website...")
        generator = InstagramSiteGenerator(data, output_dir)
        success = generator.generate()

        if success:
            print(f"\nComplete! Website generated at {output_dir}")
            return 0
        else:
            print("\nError generating website.")
            return 1

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
