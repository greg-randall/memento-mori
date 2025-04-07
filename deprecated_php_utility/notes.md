The PHP version may be easier to run on shared hosting environments and doesn't require additional packages if PHP is already installed with the necessary extensions.

## Troubleshooting

- If you see errors about GD library or WebP support, you may need to install additional PHP extensions
- For video thumbnail generation, ensure FFmpeg is installed and accessible in your system path
- For HEIC file support, ensure ImageMagick is installed
- If using Docker, ensure you have permissions to write to the output directory
- For large archives, be patient as processing media files can take time
