<?php

// Create distribution directory if it doesn't exist
if (!file_exists('distribution')) {
    mkdir('distribution', 0755, true);
}

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
      'distribution/media/other',
      'distribution/thumbnails'
  ];
  
  foreach ($media_dirs as $dir) {
      if (!file_exists($dir)) {
          mkdir($dir, 0755, true);
      }
  }
  
  // Copy profile picture
  copy_file_to_distribution($profile_picture);
  
  // Generate thumbnail for profile picture
  generate_thumbnail($profile_picture, $profile_picture);
  
  // Copy all post media
  $total_media = 0;
  $processed_media = 0;
  
  // Count total media files first
  foreach ($post_data as $post) {
      $total_media += count($post['media']);
  }
  
  fwrite(STDERR, "Generating thumbnails for $total_media media files...\n");
  
  // Process each media file
  foreach ($post_data as $post) {
      foreach ($post['media'] as $media_url) {
          copy_file_to_distribution($media_url);
          $processed_media++;
          
          // Show progress
          if ($processed_media % 10 === 0 || $processed_media === $total_media) {
              $percent = round(($processed_media / $total_media) * 100);
              fwrite(STDERR, "Progress: $processed_media/$total_media ($percent%)\n");
          }
      }
  }
  
  // Count how many thumbnails and WebP conversions were successfully generated
  $thumbnail_count = 0;
  $webp_count = 0;
  $total_size_original = 0;
  $total_size_webp = 0;
  
  if (is_dir('distribution/thumbnails')) {
      $thumbnail_count = count(glob('distribution/thumbnails/*.webp'));
  }
  
  // Count WebP conversions and calculate space savings
  foreach ($post_data as $post) {
      foreach ($post['media'] as $media_url) {
          if (preg_match('/\.(jpg|jpeg|png|gif)$/i', $media_url)) {
              $original_path = $media_url;
              $webp_path = preg_replace('/\.(jpg|jpeg|png|gif)$/i', '.webp', $media_url);
              
              if (file_exists('distribution/' . $webp_path)) {
                  $webp_count++;
                  
                  // Calculate size difference if original exists
                  if (file_exists($original_path)) {
                      $original_size = filesize($original_path);
                      $webp_size = filesize('distribution/' . $webp_path);
                      $total_size_original += $original_size;
                      $total_size_webp += $webp_size;
                  }
              }
          }
      }
  }
  
  // Calculate total space savings
  $space_saved_mb = ($total_size_original - $total_size_webp) / (1024 * 1024);
  
  fwrite(STDERR, "All media files and thumbnails processed.\n");
  fwrite(STDERR, "Successfully generated $thumbnail_count thumbnails.\n");
  fwrite(STDERR, "Successfully converted $webp_count images to WebP format.\n");
  fwrite(STDERR, sprintf("Total space saved: %.2f MB (%.1f%%)\n", 
      $space_saved_mb, 
      $total_size_original > 0 ? (($total_size_original - $total_size_webp) / $total_size_original * 100) : 0
  ));
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
  
  // Check if it's an image file that can be converted to WebP
  $is_image = preg_match('/\.(jpg|jpeg|png|gif)$/i', $file_path);
  $is_video = preg_match('/\.(mp4|mov|avi|webm)$/i', $file_path);
  
  if ($is_image && file_exists($source)) {
      // Convert image to WebP for better compression
      $webp_destination = preg_replace('/\.(jpg|jpeg|png|gif)$/i', '.webp', $destination);
      convert_to_webp($source, $webp_destination);
      
      // Generate thumbnail for this file
      generate_thumbnail($source, $file_path);
  } else if (file_exists($source)) {
      // Copy the file as is (for videos and other file types)
      copy($source, $destination);
      
      // Generate thumbnail for this file
      generate_thumbnail($source, $file_path);
  }
}

/**
 * Convert an image to WebP format without cropping
 * 
 * @param string $source_path The source image path
 * @param string $destination_path The destination WebP path
 * @return bool True if successful, false otherwise
 */
function convert_to_webp($source_path, $destination_path) {
    try {
        // Detect file type by examining file contents
        $file_info = new finfo(FILEINFO_MIME_TYPE);
        $mime_type = $file_info->file($source_path);
        
        // Create image resource based on mime type
        $source_image = null;
        
        switch ($mime_type) {
            case 'image/jpeg':
                $source_image = @imagecreatefromjpeg($source_path);
                break;
            case 'image/png':
                $source_image = @imagecreatefrompng($source_path);
                // Preserve transparency for PNG
                if ($source_image) {
                    imagepalettetotruecolor($source_image);
                    imagealphablending($source_image, true);
                    imagesavealpha($source_image, true);
                }
                break;
            case 'image/gif':
                $source_image = @imagecreatefromgif($source_path);
                break;
            default:
                // Try to load as JPEG first, then PNG, then GIF as fallbacks
                $source_image = @imagecreatefromjpeg($source_path);
                if (!$source_image) {
                    $source_image = @imagecreatefrompng($source_path);
                    if ($source_image) {
                        imagepalettetotruecolor($source_image);
                        imagealphablending($source_image, true);
                        imagesavealpha($source_image, true);
                    }
                }
                if (!$source_image) {
                    $source_image = @imagecreatefromgif($source_path);
                }
                break;
        }
        
        if (!$source_image) {
            fwrite(STDERR, "Failed to create image resource for conversion: " . $source_path . "\n");
            // Fall back to copying the original file
            copy($source_path, str_replace('.webp', '.jpg', $destination_path));
            return false;
        }
        
        // Save as WebP with 80% quality (good balance between quality and file size)
        $result = imagewebp($source_image, $destination_path, 80);
        
        // Clean up
        imagedestroy($source_image);
        
        if ($result) {
            // Check if the WebP file is actually smaller than the original
            $original_size = filesize($source_path);
            $webp_size = filesize($destination_path);
            
            if ($webp_size > 0 && $webp_size < $original_size) {
                fwrite(STDERR, "Converted to WebP: " . $source_path . " (saved " . 
                       round(($original_size - $webp_size) / 1024, 2) . " KB)\n");
                return true;
            } else {
                // If WebP is larger or failed, use the original file
                unlink($destination_path);
                copy($source_path, str_replace('.webp', '.jpg', $destination_path));
                fwrite(STDERR, "WebP larger than original, using original: " . $source_path . "\n");
                return false;
            }
        } else {
            // If WebP conversion failed, use the original file
            copy($source_path, str_replace('.webp', '.jpg', $destination_path));
            fwrite(STDERR, "WebP conversion failed, using original: " . $source_path . "\n");
            return false;
        }
    } catch (Exception $e) {
        fwrite(STDERR, "Error converting to WebP: " . $e->getMessage() . "\n");
        // Fall back to copying the original file
        copy($source_path, str_replace('.webp', '.jpg', $destination_path));
        return false;
    }
}

/**
 * Generate a thumbnail for an image or video file
 * 
 * @param string $source_path The source file path
 * @param string $relative_path The relative path for naming the thumbnail
 * @return string|null The path to the generated thumbnail or null if failed
 */
function generate_thumbnail($source_path, $relative_path) {
    // Create thumbnails directory if it doesn't exist
    $thumbs_dir = 'distribution/thumbnails';
    if (!file_exists($thumbs_dir)) {
        mkdir($thumbs_dir, 0755, true);
    }
    
    // Generate a unique filename for the thumbnail based on the original path
    $thumb_filename = md5($relative_path) . '.webp';
    $thumb_path = $thumbs_dir . '/' . $thumb_filename;
    
    // Skip if thumbnail already exists
    if (file_exists($thumb_path)) {
        return $thumb_path;
    }
    
    // Target dimensions
    $target_width = 292;
    $target_height = 292;
    
    fwrite(STDERR, "Generating thumbnail for: $relative_path\n");
    
    try {
        // Check if file exists
        if (!file_exists($source_path)) {
            fwrite(STDERR, "File not found: $source_path\n");
            return null;
        }
        
        // Detect file type by examining file contents
        $file_info = new finfo(FILEINFO_MIME_TYPE);
        $mime_type = $file_info->file($source_path);
        
        // Determine if it's a video based on mime type
        $is_video = (strpos($mime_type, 'video/') === 0);
        
        // For HEIC files (often incorrectly labeled)
        $is_heic = false;
        if (strpos($mime_type, 'application/octet-stream') === 0) {
            // Check for HEIC signature
            $file_header = file_get_contents($source_path, false, null, 0, 12);
            if (strpos($file_header, 'ftypheic') !== false || 
                strpos($file_header, 'ftypmif1') !== false || 
                strpos($file_header, 'ftyphevc') !== false) {
                $is_heic = true;
            }
        }
        
        if ($is_video) {
            // For videos, try to use FFmpeg to extract a frame
            if (function_exists('exec')) {
                $temp_jpg = tempnam(sys_get_temp_dir(), 'thumb') . '.jpg';
                // Extract a frame at 1 second mark
                exec("ffmpeg -i \"$source_path\" -ss 00:00:01 -vframes 1 -vf \"scale=$target_width:$target_height:force_original_aspect_ratio=decrease,pad=$target_width:$target_height:(ow-iw)/2:(oh-ih)/2:color=black\" \"$temp_jpg\" 2>&1", $output, $return_var);
                
                if ($return_var !== 0) {
                    fwrite(STDERR, "FFmpeg error: " . implode("\n", $output) . "\n");
                    return null;
                }
                
                // Convert the extracted frame to WebP
                if (function_exists('imagecreatefromjpeg') && function_exists('imagewebp')) {
                    $image = imagecreatefromjpeg($temp_jpg);
                    imagewebp($image, $thumb_path, 80);
                    imagedestroy($image);
                    unlink($temp_jpg); // Clean up temp file
                    return $thumb_path;
                }
            }
            
            // If FFmpeg fails or is not available, use a placeholder
            fwrite(STDERR, "Could not generate video thumbnail for: $relative_path\n");
            return null;
        } else if ($is_heic) {
            // For HEIC files, try to use ImageMagick if available
            if (function_exists('exec')) {
                $temp_jpg = tempnam(sys_get_temp_dir(), 'thumb') . '.jpg';
                exec("convert \"$source_path\" \"$temp_jpg\" 2>&1", $output, $return_var);
                
                if ($return_var !== 0) {
                    fwrite(STDERR, "ImageMagick error for HEIC: " . implode("\n", $output) . "\n");
                    return null;
                }
                
                // Now process the converted JPG
                if (file_exists($temp_jpg)) {
                    $source_image = imagecreatefromjpeg($temp_jpg);
                    if (!$source_image) {
                        fwrite(STDERR, "Failed to create image from converted HEIC: $relative_path\n");
                        unlink($temp_jpg);
                        return null;
                    }
                    
                    // Process the image (resize and save as WebP)
                    $result = process_and_save_image($source_image, $thumb_path, $target_width, $target_height);
                    unlink($temp_jpg); // Clean up temp file
                    return $result;
                }
            }
            
            fwrite(STDERR, "Could not convert HEIC file: $relative_path\n");
            return null;
        } else {
            // For images, use GD library
            if (!function_exists('imagecreatefromjpeg') || !function_exists('imagewebp')) {
                fwrite(STDERR, "GD library with WebP support is required\n");
                return null;
            }
            
            // Create image resource based on mime type
            $source_image = null;
            
            switch ($mime_type) {
                case 'image/jpeg':
                    $source_image = @imagecreatefromjpeg($source_path);
                    break;
                case 'image/png':
                    $source_image = @imagecreatefrompng($source_path);
                    break;
                case 'image/gif':
                    $source_image = @imagecreatefromgif($source_path);
                    break;
                case 'image/webp':
                    $source_image = @imagecreatefromwebp($source_path);
                    break;
                default:
                    // Try to load as JPEG first, then PNG, then GIF as fallbacks
                    $source_image = @imagecreatefromjpeg($source_path);
                    if (!$source_image) {
                        $source_image = @imagecreatefrompng($source_path);
                    }
                    if (!$source_image) {
                        $source_image = @imagecreatefromgif($source_path);
                    }
                    if (!$source_image) {
                        $source_image = @imagecreatefromwebp($source_path);
                    }
                    break;
            }
            
            if (!$source_image) {
                fwrite(STDERR, "Failed to create image resource for: $relative_path (MIME: $mime_type)\n");
                return null;
            }
            
            return process_and_save_image($source_image, $thumb_path, $target_width, $target_height);
        }
    } catch (Exception $e) {
        fwrite(STDERR, "Error generating thumbnail: " . $e->getMessage() . "\n");
        return null;
    }
    
    return null;
}

/**
 * Process an image resource and save it as a WebP thumbnail
 * 
 * @param resource $source_image The source image resource
 * @param string $thumb_path The path to save the thumbnail
 * @param int $target_width The target width
 * @param int $target_height The target height
 * @return string|null The path to the generated thumbnail or null if failed
 */
function process_and_save_image($source_image, $thumb_path, $target_width, $target_height) {
    try {
        // Get original dimensions
        $original_width = imagesx($source_image);
        $original_height = imagesy($source_image);
        
        // Create the final square thumbnail
        $thumb_image = imagecreatetruecolor($target_width, $target_height);
        
        // Fill with white background
        $white = imagecolorallocate($thumb_image, 255, 255, 255);
        imagefilledrectangle($thumb_image, 0, 0, $target_width, $target_height, $white);
        
        // Calculate dimensions for cropping to ensure 1:1 aspect ratio
        // We'll take the center portion of the image
        if ($original_width > $original_height) {
            // Landscape image: crop from the center horizontally
            $src_x = ($original_width - $original_height) / 2;
            $src_y = 0;
            $src_w = $original_height;
            $src_h = $original_height;
        } else {
            // Portrait image: crop from the center vertically
            $src_x = 0;
            $src_y = ($original_height - $original_width) / 2;
            $src_w = $original_width;
            $src_h = $original_width;
        }
        
        // Copy and resize the cropped portion directly to the thumbnail
        imagecopyresampled(
            $thumb_image, $source_image,
            0, 0, $src_x, $src_y,
            $target_width, $target_height, $src_w, $src_h
        );
        
        // Save as WebP
        imagewebp($thumb_image, $thumb_path, 80);
        
        // Clean up
        imagedestroy($source_image);
        imagedestroy($thumb_image);
        
        return $thumb_path;
    } catch (Exception $e) {
        fwrite(STDERR, "Error processing image: " . $e->getMessage() . "\n");
        return null;
    }
}



function render_instagram_grid($post_data, $lazy_after = 30) {
    $output = '';
    
    // Process each post
    $i=1;
    foreach ($post_data as $timestamp => $post) {
        if($i > $lazy_after){
            $lazy_load = ' loading="lazy"';
        } else {
            $lazy_load = '';
        }
        $index = $post['post_index'];
        $media_count = count($post['media']);
        
        // Determine which media to use for the grid thumbnail
        $display_media = '';
        $is_video = false;
        
        if (isset($post['media'][0])) {
            $first_media = $post['media'][0];
            $original_media = $first_media;
            $display_media = $first_media;
            
            // Check if first media is a video
            $is_video = preg_match('/\.(mp4|mov|avi|webm)$/i', $first_media);
            
            // Check if we have a thumbnail for this media
            $thumb_filename = md5($first_media) . '.webp';
            $thumb_path = 'thumbnails/' . $thumb_filename;
            
            if (file_exists('distribution/' . $thumb_path)) {
                // Use the thumbnail instead of the original
                $display_media = $thumb_path;
                fwrite(STDERR, "Using thumbnail for: $first_media\n");
            } else {
                // Check if we have a WebP version of the original image
                if (!$is_video) {
                    $webp_path = preg_replace('/\.(jpg|jpeg|png|gif)$/i', '.webp', $first_media);
                    if (file_exists('distribution/' . $webp_path)) {
                        $display_media = $webp_path;
                        fwrite(STDERR, "Using WebP version for: $first_media\n");
                    }
                }
                
                // If it's a video, look for a thumbnail among all media items
                if ($is_video) {
                    $found_thumbnail = false;
                    
                    // First check if there are any image files in the post's media that could be thumbnails
                    foreach ($post['media'] as $media_item) {
                        if (preg_match('/\.(jpg|jpeg|png|webp|gif)$/i', $media_item)) {
                            // Check if we have a thumbnail for this image
                            $img_thumb_filename = md5($media_item) . '.webp';
                            $img_thumb_path = 'thumbnails/' . $img_thumb_filename;
                            
                            if (file_exists('distribution/' . $img_thumb_path)) {
                                $display_media = $img_thumb_path;
                            } else {
                                $display_media = $media_item;
                            }
                            $found_thumbnail = true;
                            break;
                        }
                    }
                    
                    // If no thumbnail found, use a better SVG placeholder
                    if (!$found_thumbnail) {
                        // Create a simple SVG with a play button
                        $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">';
                        $svg .= '<rect width="400" height="400" fill="#333333"/>';
                        $svg .= '<circle cx="200" cy="200" r="60" fill="#ffffff" fill-opacity="0.8"/>';
                        $svg .= '<polygon points="180,160 180,240 240,200" fill="#333333"/>';
                        $svg .= '</svg>';
                        
                        // Encode the SVG properly for use in an img src attribute
                        $display_media = 'data:image/svg+xml;base64,' . base64_encode($svg);
                    }
                }
            }
        }
        
        $output .= '        <div class="grid-item" data-index="' . $index . '">' . "\n";
        $output .= '          <img src="' . $display_media . '" alt="Instagram post"'.$lazy_load.'>' . "\n";
        
        // Add video indicator if it's a video
        if ($is_video) {
            $output .= '          <div class="video-indicator">▶ Video</div>' . "\n";
        }
        
        if ($media_count > 1) {
            $output .= '          <div class="multi-indicator">⊞ ' . $media_count . '</div>' . "\n";
        } elseif (isset($post['Likes']) && $post['Likes'] !== '') {
            $output .= '          <div class="likes-indicator">♥ ' . $post['Likes'] . '</div>' . "\n";
        }
        
        $output .= '        </div>' . "\n";
        $i++;
    }
    
    return $output;
}

date_default_timezone_set("America/New_York");


$personal_data = file_get_contents("personal_information/personal_information/personal_information.json");
$personal_data = json_decode($personal_data,true);
$profile_picture = $personal_data['profile_user'][0]['media_map_data']['Profile Photo']['uri'];
$user_name = $personal_data['profile_user'][0]["string_map_data"]["Username"]["value"];
unset($personal_data);

//echo "profile picture: $profile_picture
//username: $user_name\n";


$location_data = file_get_contents("personal_information/information_about_you/profile_based_in.json");
$location_data  = json_decode($location_data ,true);
$location = $location_data['inferred_data_primary_location'][0]['string_map_data']['City Name']['value'];
unset($location_data);

//echo "location: $location\n";


// Function to search for posts_1.json file recursively
function find_posts_json() {
    $standard_path = 'your_instagram_activity/content/posts_1.json';
    
    // First check the standard location
    if (file_exists($standard_path)) {
        return $standard_path;
    }
    
    // If not found, search recursively
    fwrite(STDERR, "posts_1.json not found in standard location, searching directories...\n");
    
    $found_files = [];
    $iterator = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator('.', RecursiveDirectoryIterator::SKIP_DOTS)
    );
    
    foreach ($iterator as $file) {
        if ($file->getFilename() === 'posts_1.json') {
            $found_files[] = $file->getPathname();
        }
    }
    
    if (empty($found_files)) {
        fwrite(STDERR, "ERROR: Could not find posts_1.json anywhere in the directory structure.\n");
        return false;
    }
    
    // If multiple files found, use the one that seems most likely
    if (count($found_files) > 1) {
        fwrite(STDERR, "Found multiple posts_1.json files:\n");
        foreach ($found_files as $index => $path) {
            fwrite(STDERR, "  [$index] $path\n");
        }
        
        // Try to find the one in a directory with "content" or "activity" in the path
        foreach ($found_files as $path) {
            if (strpos($path, 'content') !== false || strpos($path, 'activity') !== false) {
                fwrite(STDERR, "Selected: $path\n");
                return $path;
            }
        }
        
        // If no preferred path found, use the first one
        fwrite(STDERR, "Selected: {$found_files[0]}\n");
        return $found_files[0];
    }
    
    fwrite(STDERR, "Found posts_1.json at: {$found_files[0]}\n");
    return $found_files[0];
}

// Load and decode the JSON files
$insights_data = file_get_contents('logged_information/past_instagram_insights/posts.json');
$insights_data = json_decode($insights_data, true);

$posts_json_path = find_posts_json();
if (!$posts_json_path) {
    die("ERROR: Could not find the posts_1.json file. Please ensure your Instagram data is properly extracted.");
}
$post_data = file_get_contents($posts_json_path);
$post_data = json_decode($post_data, true);

// Create an indexed array of insights data using creation_timestamp as key
$indexed_insights = [];
foreach ($insights_data['organic_insights_posts'] as $insight) {
    $timestamp = $insight['media_map_data']['Media Thumbnail']['creation_timestamp'];
    $indexed_insights[$timestamp] = $insight;
}

// Combine the data
$combined_data = [];
foreach ($post_data as $post) {
    // Get the timestamp from the first media item (since a post might have multiple media items)
    $timestamp = $post['media'][0]['creation_timestamp'];
    
    // Create the combined post object
    $combined_post = [
        'post_data' => $post,
        'insights' => isset($indexed_insights[$timestamp]) ? $indexed_insights[$timestamp] : null
    ];
    
    // Add to combined data array
    $combined_data[] = $combined_post;
}

unset($post_data);
unset($insights_data);
unset($indexed_insights);

function extractRelevantData($combined_data) {
    $simplified_data = [];

    foreach ($combined_data as $index => $item) {
        // Initialize a new post entry
        $post_entry = [
            'post_index' => $index,
            'media' => [],
            'creation_timestamp_unix' => "",
            'creation_timestamp_readable' => "",
            'title' => "",
            'Impressions' => "",
            'Likes' => "",
            'Comments' => ""
        ];
        
        // Extract post-level data
        if (isset($item['post_data'])) {
            if (isset($item['post_data']['creation_timestamp'])) {
                $post_entry['creation_timestamp_unix'] = $item['post_data']['creation_timestamp'];
            } elseif (isset($item['post_data']['media'][0]['creation_timestamp'])) {
                // Fallback to first media item timestamp if post timestamp not available
                $post_entry['creation_timestamp_unix'] = $item['post_data']['media'][0]['creation_timestamp'];
            }

   
            $post_entry['creation_timestamp_readable'] = gmdate("F j, Y \a\\t g:i A", $post_entry['creation_timestamp_unix']);

            
            if (isset($item['post_data']['title'])) {
                $post_entry['title'] = $item['post_data']['title'];
            }
            
            // Extract media URIs
            if (isset($item['post_data']['media'])) {
                foreach ($item['post_data']['media'] as $media) {
                    $post_entry['media'][] = $media['uri'] ?? "";
                }
            }
        }
        
        // Get insights data if available
        if (isset($item['insights']) && isset($item['insights']['string_map_data'])) {
            $insights = $item['insights']['string_map_data'];
            
            // Extract specific metrics and ensure they're integers or blank
            if (isset($insights['Impressions'])) {
                $impressions = $insights['Impressions']['value'] ?? "";
                // Validate and convert to integer if numeric, otherwise leave blank
                $post_entry['Impressions'] = is_numeric($impressions) ? (int)$impressions : "";
            }
            
            if (isset($insights['Likes'])) {
                $likes = $insights['Likes']['value'] ?? "";
                // Validate and convert to integer if numeric, otherwise leave blank
                $post_entry['Likes'] = is_numeric($likes) ? (int)$likes : "";
            }
            
            if (isset($insights['Comments'])) {
                $comments = $insights['Comments']['value'] ?? "";
                // Validate and convert to integer if numeric, otherwise leave blank
                $post_entry['Comments'] = is_numeric($comments) ? (int)$comments : "";
            }
        }
        
        $simplified_data[$post_entry['creation_timestamp_unix']] = $post_entry;
        
    }

    krsort($simplified_data);
    return $simplified_data;
}

$post_data = extractRelevantData($combined_data);
unset($combined_data);



echo "<br><br><br>";

// Assuming your array is stored in $post_data
$keys = array_keys($post_data);

// Get first and last keys
$first_key = reset($keys); // Or $keys[0]
$last_key = end($keys);    // Or $keys[count($keys) - 1]

// Get timestamps from first and last elements
$last_timestamp = gmdate("F Y",$post_data[$first_key]['creation_timestamp_unix']);
$first_timestamp = gmdate("F Y",$post_data[$last_key]['creation_timestamp_unix']);

//echo"<pre>" . print_r($post_data[],true) ."</pre>";



?>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memento Mori</title>
    <link rel="stylesheet" href="style.css">
    <!-- Script to make post data available to JavaScript -->
    <script>
        window.postData = <?php echo json_encode($post_data); ?>;
    </script>
    <?php
    // Include the modal.js content directly in the output
    echo '<script>';
    echo file_get_contents('modal.js');
    echo '</script>';
    ?>
  </head>
  <body class="vsc-initialized">
    <header>
      <div class="header-content">
        <a href="https://github.com/greg-randall/memento-mori" class="logo">Memento Mori</a>
        <div class="date-range-header" id="date-range-header"><?php echo "$first_timestamp - $last_timestamp"; ?></div>
      </div>
    </header>
    <main>
      <div class="loading" id="loadingPosts" style="display: none;"> Loading posts... </div>
      <div class="profile-info">
        <div class="profile-picture">
          <img alt="Profile Picture" src="<?php echo $profile_picture; ?>" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
        </div>
        <div class="profile-details">
          <h1 id="username"><?php echo $user_name; ?></h1>
          <div class="stats">
            <div class="stat">
              <span class="stat-count" id="post-count"><?php echo count($post_data); ?></span> posts
            </div>
          </div>
        </div>
      </div>
      <div class="sort-options">
        <div class="sort-row">
          <a href="#" class="sort-link active" data-sort="newest">Newest</a>
          <a href="#" class="sort-link" data-sort="oldest">Oldest</a>
          <a href="#" class="sort-link" data-sort="most-likes">Most Likes</a>
          <a href="#" class="sort-link" data-sort="most-comments">Most Comments</a>
          <a href="#" class="sort-link" data-sort="most-views">Most Views</a>
          <a href="#" class="sort-link" data-sort="random">Random</a>
        </div>
      </div>
      <div class="posts-grid" id="postsGrid">
        <?php echo render_instagram_grid($post_data); ?>
        </div>
       
    </main>

    <!-- Modal for post details -->
    <div class="post-modal" id="postModal">
        <div class="close-modal" id="closeModal">✕</div>
        <div class="modal-nav modal-prev" id="modalPrev">❮</div>
        <div class="modal-nav modal-next" id="modalNext">❯</div>
        <div class="post-modal-content">
            <div class="post-media" id="postMedia"></div>
            <div class="post-info">
                <div class="post-header">
                    <div class="post-user" id="postUserPic">
                        <img src="<?php echo $profile_picture; ?>" alt="Profile" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                    </div>
                    <div class="post-username" id="postUsername"><?php echo $user_name; ?></div>
                </div>
                <div class="post-caption" id="postCaption"></div>
                <div class="post-stats" id="postStats"></div>
                <div class="post-date" id="postDate"></div>
            </div>
        </div>
    </div>
  </body>
</html>

<?php
// Copy media files and generate thumbnails first
copy_media_files($post_data, $profile_picture);

// Now start output buffering to capture HTML after thumbnails are generated
ob_start();

// Include the HTML generation code here
?>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memento Mori</title>
    <link rel="stylesheet" href="style.css">
    <!-- Script to make post data available to JavaScript -->
    <script>
        window.postData = <?php echo json_encode($post_data); ?>;
        
        // Function to copy the current URL to clipboard
        function copyCurrentUrl() {
            const url = window.location.href;
            navigator.clipboard.writeText(url)
                .then(() => {
                    alert('Link copied to clipboard!');
                })
                .catch(err => {
                    console.error('Could not copy URL: ', err);
                });
        }
    </script>
    <?php
    // Include the modal.js content directly in the output
    echo '<script>';
    echo file_get_contents('modal.js');
    echo '</script>';
    ?>
  </head>
  <body class="vsc-initialized">
    <header>
      <div class="header-content">
        <a href="https://github.com/greg-randall/memento-mori" class="logo">Memento Mori</a>
        <div class="date-range-header" id="date-range-header"><?php echo "$first_timestamp - $last_timestamp"; ?></div>
      </div>
    </header>
    <main>
      <div class="loading" id="loadingPosts" style="display: none;"> Loading posts... </div>
      <div class="profile-info">
        <div class="profile-picture">
          <img alt="Profile Picture" src="<?php echo $profile_picture; ?>" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
        </div>
        <div class="profile-details">
          <h1 id="username"><?php echo $user_name; ?></h1>
          <div class="stats">
            <div class="stat">
              <span class="stat-count" id="post-count"><?php echo count($post_data); ?></span> posts
            </div>
          </div>
        </div>
      </div>
      <div class="sort-options">
        <div class="sort-row">
          <a href="#" class="sort-link active" data-sort="newest">Newest</a>
          <a href="#" class="sort-link" data-sort="oldest">Oldest</a>
          <a href="#" class="sort-link" data-sort="most-likes">Most Likes</a>
          <a href="#" class="sort-link" data-sort="most-comments">Most Comments</a>
          <a href="#" class="sort-link" data-sort="most-views">Most Views</a>
          <a href="#" class="sort-link" data-sort="random">Random</a>
        </div>
      </div>
      <div class="posts-grid" id="postsGrid">
        <?php echo render_instagram_grid($post_data); ?>
        </div>
       
    </main>

    <!-- Modal for post details -->
    <div class="post-modal" id="postModal">
        <div class="close-modal" id="closeModal">✕</div>
        <div class="modal-nav modal-prev" id="modalPrev">❮</div>
        <div class="modal-nav modal-next" id="modalNext">❯</div>
        <div class="post-modal-content">
            <div class="post-media" id="postMedia"></div>
            <div class="post-info">
                <div class="post-header">
                    <div class="post-user" id="postUserPic">
                        <img src="<?php echo $profile_picture; ?>" alt="Profile" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;">
                    </div>
                    <div class="post-username" id="postUsername"><?php echo $user_name; ?></div>
                </div>
                <div class="post-caption" id="postCaption"></div>
                <div class="post-stats" id="postStats"></div>
                <div class="post-date" id="postDate"></div>
            </div>
        </div>
    </div>
  </body>
</html>
<?php
// Get the HTML content
$html_content = ob_get_contents();
ob_end_clean();

// Write the HTML to the distribution folder
file_put_contents('distribution/index.html', $html_content);

// Copy the CSS file to the distribution folder
if (file_exists('style.css')) {
    copy('style.css', 'distribution/style.css');
    fwrite(STDERR, "CSS file copied to distribution folder.\n");
}

// Verify all images in the HTML are accessible
fwrite(STDERR, "Verifying all images in the generated HTML...\n");
verify_images_in_html($html_content);

// Output the content to the browser as well
echo $html_content;

/**
 * Verify that all images referenced in the HTML actually exist
 * 
 * @param string $html_content The HTML content to check
 */
function verify_images_in_html($html_content) {
    // Extract all image sources from the HTML
    preg_match_all('/<img[^>]+src=([\'"])([^"\']+)\\1/i', $html_content, $matches);
    
    $image_sources = $matches[2];
    $total_images = count($image_sources);
    $missing_images = 0;
    $fixed_images = 0;
    
    fwrite(STDERR, "Found $total_images image references to verify.\n");
    
    foreach ($image_sources as $src) {
        // Skip data URIs
        if (strpos($src, 'data:image') === 0) {
            continue;
        }
        
        // Check if the image exists in the distribution folder
        $image_path = 'distribution/' . $src;
        
        if (!file_exists($image_path)) {
            $missing_images++;
            fwrite(STDERR, "Missing image: $src\n");
            
            // Try to find the image with a different extension
            $base_path = pathinfo($image_path, PATHINFO_DIRNAME) . '/' . pathinfo($image_path, PATHINFO_FILENAME);
            $found = false;
            
            // Check common image extensions
            foreach (['.jpg', '.jpeg', '.png', '.gif', '.webp'] as $ext) {
                $alt_path = $base_path . $ext;
                if (file_exists($alt_path)) {
                    fwrite(STDERR, "  Found alternative: " . basename($alt_path) . "\n");
                    
                    // Copy the file to the expected path
                    copy($alt_path, $image_path);
                    $fixed_images++;
                    $found = true;
                    break;
                }
            }
            
            if (!$found) {
                // Check if the original file exists (before distribution)
                $original_src = $src;
                if (file_exists($original_src)) {
                    fwrite(STDERR, "  Found original file, copying to distribution: $original_src\n");
                    
                    // Create directory if it doesn't exist
                    $dir = dirname($image_path);
                    if (!file_exists($dir)) {
                        mkdir($dir, 0755, true);
                    }
                    
                    // Copy the file
                    copy($original_src, $image_path);
                    $fixed_images++;
                }
            }
        }
    }
    
    // Report results
    if ($missing_images === 0) {
        fwrite(STDERR, "All images verified successfully!\n");
    } else {
        fwrite(STDERR, "Found $missing_images missing images, fixed $fixed_images.\n");
        if ($missing_images > $fixed_images) {
            fwrite(STDERR, "WARNING: " . ($missing_images - $fixed_images) . " images could not be fixed.\n");
        }
    }
}
?>

