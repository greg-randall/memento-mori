# Memento Mori - Your Instagram Archive Viewer

![Memento Mori](https://img.shields.io/badge/Memento-Mori-E4405F?style=for-the-badge&logo=instagram&logoColor=white)

## 🌟 Overview

**Memento Mori** is a standalone, offline Instagram archive viewer that helps you explore and reflect on your digital legacy. The name "Memento Mori" (Latin for "remember that you will die") reminds us that our digital footprints, like our lives, are temporary yet meaningful.

This tool allows you to browse through your Instagram posts, photos, and videos in a familiar interface without requiring an internet connection or Instagram account. It works directly with the data export that Instagram provides to users.

## 🎯 Who Is This For?

- **Privacy-conscious users** who want to view their Instagram content without being online
- **Digital archivists** preserving social media history
- **People leaving Instagram** but wanting to keep their memories accessible
- **Nostalgic browsers** who enjoy reflecting on past posts and memories
- **Digital minimalists** who have deleted their accounts but saved their data

## ✨ Features

- **Clean, Instagram-like interface** that feels familiar
- **Works 100% offline** - no internet connection required
- **View photos, videos, and carousels** just like on Instagram
- **Read your original captions** and see post dates
- **Browse chronologically** through your digital memories
- **Responsive design** that works on desktop and mobile devices
- **No tracking or data collection** - your data stays on your device

## 🚀 Getting Started

### Prerequisites

- Your Instagram data export (JSON format)
- A modern web browser (Chrome, Firefox, Safari, Edge)

### How to Use

1. **Request your Instagram data**:
   - Go to Instagram > Settings > Privacy and Security > Data Download
   - Request data in JSON format (important!)
   - Wait for Instagram to email you the download link

2. **Set up Memento Mori**:
   - Download this repository
   - Extract your Instagram data archive into the same folder as this project
   - Make sure the folder structure includes `your_instagram_activity/content/posts_1.json`

3. **Launch the viewer**:
   - Open `index.html` in your web browser
   - Your posts should load automatically

## 📁 File Structure

Your folder should look like this:

```
memento-mori/
├── index.html                 # The main viewer file
├── README.md                  # This file
└── your_instagram_activity/   # From your Instagram export
    └── content/
        └── posts_1.json       # Your posts data
```

## 🔍 Troubleshooting

- **No posts showing?** Make sure your Instagram export is in JSON format and the file paths match the expected structure.
- **Media not loading?** Instagram exports can sometimes have inconsistent file paths. Try moving your media files to match the paths in the JSON.
- **Videos not playing?** Some browsers have restrictions on local video playback. Try using Chrome or Firefox.

## 🛠️ Technical Details

Memento Mori is built with vanilla JavaScript, HTML, and CSS. It doesn't require any server, database, or external libraries. It processes your Instagram JSON data locally in your browser and displays it in a familiar format.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests if you have ideas for improvements.

## 📝 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Inspired by the concept of digital legacy and preservation
- Designed for those who value their digital memories but prefer offline browsing

---

*Remember, your digital footprint tells a story. Memento Mori helps you preserve and reflect on that story, offline and on your own terms.*
