# Memento Mori - Instagram Archive Viewer

## Overview

**Memento Mori** is a tool that converts your Instagram data export into a beautiful, standalone viewer that resembles the Instagram interface. The name "Memento Mori" (Latin for "remember that you will die") reflects the ephemeral nature of our digital content.

![Memento Mori Interface Preview](preview.gif)

## How It Works

Memento Mori processes your Instagram data export and generates a static site with your posts, copying all your media files into an organized structure that can be viewed offline or hosted on your own website.

## How to Use

1. Request and download your Instagram data archive (Settings > Privacy and Security > Data Download)
2. Extract the archive to a folder
3. Place the Memento Mori files in the same folder as your extracted archive
4. Run the PHP script: `php index.php`
5. A `distribution` folder will be created containing your Instagram archive viewer and media files
6. Open `distribution/index.html` in your browser or upload the entire distribution folder to your web hosting

You can also view the site directly in your browser while running the PHP script, as it outputs the HTML content to the browser as well as saving it to the distribution folder.

**DO NOT** share your raw Instagram export online, there's data you probably don't want to share, phone number, precise location data, personal messages, etc!!!

## Why This Exists

Instagram, like many social platforms, has undergone significant "enshittification" - a term coined to describe how platforms evolve:

1. First, they attract users with a quality experience
2. Then, they leverage their position to extract data and attention
3. Finally, they degrade the user experience to maximize profit

When requesting your data from Instagram, the export you receive contains all your content but in a format that's intentionally difficult to navigate and enjoy. Memento Mori solves this problem by transforming your archive into an intuitive, familiar interface that brings your memories back to life.

## Requirements

- PHP (to run the generator script)
- Your Instagram data export (in the original folder structure)

## Features

- Displays your posts in a familiar Instagram-like grid
- Shows post details, like counts, and impression statistics when clicking on a post
- Supports multiple images per post with carousel navigation
- Plays videos with native controls
- Fully responsive design that works on mobile and desktop
- Copies all your media files to the distribution folder, maintaining the original structure
- Shareable links to specific posts
