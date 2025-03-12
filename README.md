# Memento Mori - Instagram Archive Viewer

![Memento Mori](https://img.shields.io/badge/Memento-Mori-E4405F?style=for-the-badge&logo=instagram&logoColor=white)

## Overview

**Memento Mori** is a standalone, offline Instagram archive viewer that lets you browse your exported Instagram data in a familiar interface. The name "Memento Mori" (Latin for "remember that you will die") reflects the ephemeral nature of our digital content.

## Why This Exists

Instagram, like many social platforms, has undergone significant "enshittification" - a term coined to describe how platforms evolve:

1. First, they attract users with a quality experience
2. Then, they leverage their position to extract data and attention
3. Finally, they degrade the user experience to maximize profit

This progression has led to:
- Algorithmic feeds that prioritize engagement over chronology
- Increasing ad density and sponsored content
- Privacy concerns and data harvesting
- Feature bloat that complicates the original experience

**Memento Mori** lets you reclaim your content and view it on your terms - offline, private, and without the noise.

## Features

- **Works 100% offline** - no internet connection or account required
- **Clean, Instagram-like interface** without ads or algorithmic sorting
- **View photos, videos, and carousels** in their original quality
- **Read your original captions and comments**
- **Browse chronologically** - the way social media used to work
- **Responsive design** for desktop and mobile viewing
- **Zero tracking or data collection** - your data stays on your device
- **No dependencies** - pure HTML, CSS, and JavaScript

## Getting Started

### Prerequisites

- Your Instagram data export (JSON format)
- A modern web browser

### How to Use

1. **Export your Instagram data**:
   - Go to Instagram > Settings > Privacy and Security > Data Download
   - Request data in JSON format (not HTML)
   - Wait for Instagram to email you the download link (can take hours or days)

2. **Set up Memento Mori**:
   - Download this repository
   - Extract your Instagram data archive into the same folder
   - Ensure the folder structure includes `your_instagram_activity/content/posts_1.json`

3. **View your archive**:
   - Open `index.html` in any modern browser
   - No server needed - everything runs locally in your browser

## File Structure

```
memento-mori/
├── index.html                 # The viewer application
├── README.md                  # This documentation
└── your_instagram_activity/   # Your Instagram export
    └── content/
        └── posts_1.json       # Your posts data
```

## Troubleshooting

- **No posts showing?** Verify your export is in JSON format and the file paths match.
- **Media not loading?** Instagram exports sometimes have inconsistent paths. Check the console for errors.
- **Videos not playing?** Try Chrome or Firefox, which have better support for local video playback.
- **Slow performance?** Large archives with many videos may load slowly. Be patient on first load.

## Privacy & Security

- This tool runs entirely in your browser
- No data is sent to any server
- No cookies or local storage used
- No tracking or analytics
- No external dependencies or CDNs

## Technical Details

Built with vanilla JavaScript, HTML, and CSS. No build process, frameworks, or external libraries.

## License

MIT License

---

*Reclaim your content. View your memories on your terms.*
