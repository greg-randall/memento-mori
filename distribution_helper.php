<?php

/**
 * Helper functions for creating the static distribution
 */

/**
 * Copy media files to the distribution folder
 * 
 * @param array $post_data The post data containing media URLs
 * @param string $profile_picture The profile picture URL
 */
function copy_media_files($post_data, $profile_picture) {
    // Create media directories in distribution folder
    $media_dirs = [
        'distribution/media',
        'distribution/media/posts',
        'distribution/media/other'
    ];
    
    foreach ($media_dirs as $dir) {
        if (!file_exists($dir)) {
            mkdir($dir, 0755, true);
        }
    }
    
    // Copy profile picture
    copy_file_to_distribution($profile_picture);
    
    // Copy all post media
    foreach ($post_data as $post) {
        foreach ($post['media'] as $media_url) {
            copy_file_to_distribution($media_url);
        }
    }
    
    echo "Media files copied to distribution folder.\n";
}

/**
 * Copy a single file to the distribution folder, maintaining its path structure
 * 
 * @param string $file_path The path to the file
 */
function copy_file_to_distribution($file_path) {
    // Skip if it's already a data URI
    if (strpos($file_path, 'data:image') === 0) {
        return;
    }
    
    $source = $file_path;
    $destination = 'distribution/' . $file_path;
    
    // Create directory structure if it doesn't exist
    $dir = dirname($destination);
    if (!file_exists($dir)) {
        mkdir($dir, 0755, true);
    }
    
    // Copy the file
    if (file_exists($source)) {
        copy($source, $destination);
    }
}

/**
 * Copy CSS files to the distribution folder
 */
function copy_css_files() {
    // If you have separate CSS files, copy them here
    // For now, CSS is embedded in the HTML
}

/**
 * Copy JavaScript files to the distribution folder
 */
function copy_js_files() {
    // If you have separate JS files (other than modal.js which is embedded), copy them here
}

?>
