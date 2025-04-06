# Memento Mori - Instagram Archive Viewer

## Project Overview

Memento Mori is a tool that transforms your Instagram data export into a beautiful, standalone viewer that resembles the Instagram interface. The name "Memento Mori" (Latin for "remember that you will die") reflects the ephemeral nature of digital content.

This README outlines the architecture for refactoring the project from a single script into a modular package that supports:
- Automatic detection and extraction of Instagram exports
- Modular processing of media and data
- Docker-based execution
- Extensible architecture for future enhancements

## Architecture

The project follows a modular architecture that separates concerns while maintaining simplicity:

### Core Components

1. **File Mapping** (`file_mapper.py`)
   - Central source of truth for file discovery patterns
   - Discovers and maps files in Instagram export structure
   - Provides consistent file access for all components

2. **Archive Extraction** (`extractor.py`)
   - Detects and extracts Instagram data archives
   - Identifies required files in the archive structure
   - Creates a file mapper instance for use by other components

3. **Data Loading & Processing** (`loader.py`)
   - Loads JSON data from Instagram export using file mapper
   - Processes and merges posts with insights
   - Creates structured data models

4. **Media Processing** (`media.py`)
   - Converts images to optimized formats (WebP)
   - Generates thumbnails for images and videos
   - Organizes media files in the output directory

5. **Website Generation** (`generator.py`)
   - Creates HTML/CSS/JS files using templates
   - Renders Instagram-like interface
   - Verifies output for completeness

6. **Command Line Interface** (`cli.py`)
   - Processes command-line arguments
   - Coordinates the execution flow
   - Provides user feedback

## Project Structure

```
memento-mori/
├── pyproject.toml               # Package metadata and dependencies
├── README.md                    # Documentation
├── Dockerfile                   # Docker container configuration
├── docker-compose.yml           # For easy Docker operation
├── memento_mori/
│   ├── __init__.py              # Package version, exports
│   ├── cli.py                   # Command-line interface
│   ├── config.py                # Configuration handling
│   ├── file_mapper.py           # File discovery and mapping
│   ├── extractor.py             # Archive detection and extraction
│   ├── loader.py                # Load and process Instagram data
│   ├── media.py                 # Media processing (conversion, thumbnails)
│   ├── generator.py             # Website generation
│   ├── templates/               # HTML templates
│   │   ├── index.html           # Main template
│   │   └── components/          # Reusable components
│   │       └── modal.html       # Post modal component
│   ├── static/                  # Static assets
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       └── modal.js
│   └── utils.py                 # Common utilities and helpers
└── tests/                       # Tests directory
```

## Component Details

### file_mapper.py

Provides a central location for file discovery and mapping:
- Defines patterns for locating important files in Instagram exports
- Discovers files based on patterns and maps them to easy-to-use identifiers
- Ensures consistency between different components accessing the same files
- Provides validation for required files
- Handles variations in Instagram export structure gracefully

### extractor.py

Responsible for locating and extracting Instagram data archives:
- Auto-detection of ZIP files in specified directories
- Extraction of archives to temporary or specified locations
- Creates a file_mapper instance for the extracted content
- Validation of extracted content structure via file_mapper
- Cleanup of temporary files after processing

### loader.py

Handles loading and processing Instagram data:
- Uses file_mapper to access JSON files (posts, insights, user data)
- Parsing and merging data sources
- Converting timestamps and other data formatting
- Providing a clean data structure for the generator

### media.py

Manages all media processing operations:
- Converting images to WebP format when beneficial
- Generating thumbnails for grid view
- Creating video thumbnails using appropriate libraries
- Parallel processing of media files
- Tracking conversion statistics

### generator.py

Creates the static website:
- Using templates instead of hardcoded HTML
- Generating responsive layout
- Including JavaScript for interactive features
- Verifying output completeness
- Supporting customization options

### cli.py

Provides command-line interface:
- Processing command-line arguments
- Validating inputs
- Coordinating processing flow 
- Using the file_mapper for consistent file access
- Reporting progress and statistics

## Processing Flow

The typical processing flow is:

```python
# Initialize extractor
extractor = InstagramArchiveExtractor()

# Extract archive
extractor.auto_detect_archive()
extraction_dir = extractor.extract()

# Get file mapper from extractor
file_mapper = extractor.file_mapper

# Initialize loader with the same file mapper
loader = InstagramDataLoader(extraction_dir, file_mapper)

# Load and process data
data = loader.load_all_data()

# Generate website with the loaded data
generator = WebsiteGenerator(data, output_dir)
generator.generate()
```

## Implementation Roadmap

### Phase 1: Basic Structure
1. Create package structure
2. Implement file_mapper for centralized file discovery
3. Move core functionality from original script to appropriate modules
4. Create basic CLI

### Phase 2: Features
1. Implement archive auto-detection
2. Add archive extraction
3. Implement templating system
4. Enhance media processing

### Phase 3: Packaging & Deployment
1. Create Docker configuration
2. Set up package installation
3. Add documentation
4. Create tests

## Docker Usage

The Docker configuration will allow easy execution:

```
# Run using docker-compose
docker-compose run --rm memento-mori --input /input/instagram-export.zip --output /output

# Or directly with docker
docker run -v $(pwd)/input:/input -v $(pwd)/output:/output memento-mori --input /input/instagram-export.zip
```

## CLI Usage

```
Usage: memento-mori [OPTIONS]

Options:
  --input PATH         Path to Instagram data (ZIP or folder)
  --output PATH        Output directory for generated website [default: ./distribution]
  --threads INTEGER    Number of parallel processing threads [default: auto]
  --auto-detect        Auto-detect Instagram export in current directory
  --quality INTEGER    WebP conversion quality (1-100) [default: 80]
  --thumbnail-size WxH Size of thumbnails [default: 292x292]
  --help               Show this message and exit
```

## Future Extensions

The architecture supports several planned extensions:
1. Multiple archive merging
2. Custom themes
3. Additional statistics and visualizations
4. Progressive enhancement of the viewer
5. Support for Stories and other Instagram content types
6. Support for different Instagram export formats as they evolve
