# __init__.py
"""
Memento Mori - Instagram Archive Viewer

A tool that converts your Instagram data export into a beautiful, standalone viewer that
resembles the Instagram interface. The name "Memento Mori" (Latin for "remember that
you will die") reflects the ephemeral nature of our digital content.
"""

__version__ = "0.1.0"

# Import main classes for easier access
from .extractor import InstagramArchiveExtractor
from .file_mapper import InstagramFileMapper
from .loader import InstagramDataLoader
from .media import InstagramMediaProcessor
from .generator import InstagramSiteGenerator

# Define what's available when using `from memento_mori import *`
__all__ = [
    "InstagramArchiveExtractor",
    "InstagramFileMapper",
    "InstagramDataLoader",
    "InstagramMediaProcessor",
    "InstagramSiteGenerator",
]
