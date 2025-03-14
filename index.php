<?php


function render_instagram_grid($post_data, $lazy_after = 30) {
    $output = '';
    
    // Process each post
    $i=1;
    foreach ($post_data as $timestamp => $post) {
        if($i<=$lazy_after){
            $lazy_load = ' loading="lazy"';
        }
        $index = $post['post_index'];
        $media_count = count($post['media']);
        $first_media = isset($post['media'][0]) ? $post['media'][0] : '';
        
        $output .= '        <div class="grid-item" data-index="' . $index . '">' . "\n";
        $output .= '          <img src="' . $first_media . '" alt="Instagram post"'.$lazy_load.'>' . "\n";
        
        if ($media_count > 1) {
            $output .= '          <div class="multi-indicator">⊞ ' . $media_count . '</div>' . "\n";
        } elseif (isset($post['Likes']) && $post['Likes'] !== '') {
            $output .= '          <div class="likes-indicator">♥ ' . $post['Likes'] . '</div>' . "\n";
        }
        
        $output .= '        </div>' . "\n";
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


// Load and decode the JSON files
$insights_data = file_get_contents('logged_information/past_instagram_insights/posts.json');
$insights_data = json_decode($insights_data, true);

$post_data = file_get_contents('your_instagram_activity/content/posts_1.json');
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
    <style>
      :root {
        --instagram-bg: #fafafa;
        --instagram-border: #dbdbdb;
        --instagram-text: #262626;
        --instagram-link: #0095f6;
        --header-height: 60px;
      }

      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }

      body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: var(--instagram-bg);
        color: var(--instagram-text);
        line-height: 1.5;
      }

      header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: var(--header-height);
        background-color: white;
        border-bottom: 1px solid var(--instagram-border);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 20px;
        z-index: 100;
      }

      .header-content {
        max-width: 975px;
        width: 100%;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .logo {
        font-size: 24px;
        font-weight: bold;
        color: var(--instagram-text);
        text-decoration: none;
      }

      main {
        max-width: 975px;
        margin: calc(var(--header-height) + 30px) auto 30px;
        padding: 0 20px;
      }

      .profile-info {
        display: flex;
        align-items: center;
        margin-bottom: 30px;
      }

      .profile-picture {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 30px;
        background-color: #eee;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 36px;
        color: #aaa;
      }

      .profile-details h1 {
        font-size: 28px;
        font-weight: 300;
        margin-bottom: 15px;
      }

      .stats {
        display: flex;
        margin-bottom: 15px;
        font-size: 16px;
      }

      .stat {
        margin-right: 40px;
      }

      .stat-count {
        font-weight: 600;
      }

      .posts-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 28px;
      }

      .grid-item {
        position: relative;
        aspect-ratio: 1;
        cursor: pointer;
        overflow: hidden;
      }

      .grid-item img,
      .grid-item video {
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.3s ease;
      }

      .grid-item:hover img,
      .grid-item:hover video {
        transform: scale(1.05);
      }

      .multi-indicator {
        position: absolute;
        top: 10px;
        right: 10px;
        color: white;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 2;
      }

      .video-indicator {
        position: absolute;
        top: 10px;
        right: 10px;
        color: white;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 2;
      }

      .post-modal {
        display: none;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.9);
        z-index: 1000;
        overflow-y: auto;
      }

      .post-modal-content {
        display: flex;
        max-width: 1200px;
        margin: 30px auto;
        background-color: white;
        height: calc(100vh - 60px);
        max-height: 800px;
        border-radius: 4px;
        overflow: hidden;
      }

      .post-media {
        flex: 1;
        background-color: black;
        position: relative;
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .post-media img,
      .post-media video {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }

      .post-info {
        width: 340px;
        border-left: 1px solid var(--instagram-border);
        display: flex;
        flex-direction: column;
      }

      .post-header {
        padding: 16px;
        border-bottom: 1px solid var(--instagram-border);
        display: flex;
        align-items: center;
      }

      .post-user {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        margin-right: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #eee;
        font-size: 14px;
        color: #aaa;
      }

      .post-username {
        font-weight: 600;
      }

      .post-caption {
        padding: 16px;
        flex-grow: 1;
        overflow-y: auto;
      }

      .post-date {
        padding: 16px;
        color: #8e8e8e;
        font-size: 12px;
        border-top: 1px solid var(--instagram-border);
      }

      .post-stats {
        padding: 12px 16px;
        color: var(--instagram-text);
        font-size: 14px;
        border-top: 1px solid var(--instagram-border);
        display: flex;
        gap: 16px;
      }

      .post-stat {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .post-stat-icon {
        font-size: 16px;
      }

      .likes-indicator {
        position: absolute;
        bottom: 10px;
        left: 10px;
        color: white;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 12px;
        z-index: 2;
      }

      .close-modal {
        position: absolute;
        top: 20px;
        right: 20px;
        color: white;
        font-size: 30px;
        cursor: pointer;
        z-index: 1001;
      }

      .modal-nav {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        color: white;
        font-size: 30px;
        cursor: pointer;
        z-index: 1001;
        background-color: rgba(0, 0, 0, 0.5);
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .modal-prev {
        left: 20px;
      }

      .modal-next {
        right: 20px;
      }

      .slideshow-nav {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        color: white;
        font-size: 30px;
        cursor: pointer;
        z-index: 5;
        background-color: rgba(0, 0, 0, 0.7);
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background-color 0.2s;
      }

      .slideshow-nav:hover {
        background-color: rgba(0, 0, 0, 0.9);
      }

      .slideshow-prev {
        left: 10px;
      }

      .slideshow-next {
        right: 10px;
      }

      .slideshow-indicator {
        position: absolute;
        bottom: 20px;
        left: 0;
        right: 0;
        display: flex;
        justify-content: center;
        z-index: 5;
        background-color: rgba(0, 0, 0, 0.3);
        padding: 8px 0;
        border-radius: 20px;
        width: auto;
        max-width: 80%;
        margin: 0 auto;
      }

      .slideshow-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: rgba(255, 255, 255, 0.5);
        margin: 0 4px;
        cursor: pointer;
        transition: background-color 0.2s;
      }

      .slideshow-dot:hover {
        background-color: rgba(255, 255, 255, 0.8);
      }

      .slideshow-dot.active {
        background-color: white;
      }

      .media-container {
        position: relative;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .media-slide {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
      }

      .media-slide img,
      .media-slide video {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
      }

      .media-slide.active {
        opacity: 1;
        z-index: 2;
        pointer-events: auto;
      }

      .media-slide.active {
        opacity: 1;
        z-index: 2;
      }

      .file-input-container {
        margin-bottom: 20px;
        padding: 20px;
        background-color: white;
        border: 1px solid var(--instagram-border);
        border-radius: 4px;
      }

      .loading {
        text-align: center;
        padding: 40px;
        font-size: 18px;
      }

      @media (max-width: 768px) {
        .posts-grid {
          grid-template-columns: repeat(2, 1fr);
          gap: 4px;
        }

        .post-modal-content {
          flex-direction: column;
          height: auto;
          max-height: none;
          margin: 0;
          border-radius: 0;
        }

        .post-media {
          height: 50vh;
        }

        .post-info {
          width: 100%;
          border-left: none;
          border-top: 1px solid var(--instagram-border);
        }

        .profile-picture {
          width: 80px;
          height: 80px;
          margin-right: 15px;
        }

        .stat {
          margin-right: 20px;
        }
      }

      @media (max-width: 480px) {
        .posts-grid {
          grid-template-columns: repeat(3, 1fr);
          gap: 3px;
        }

        .profile-info {
          flex-direction: column;
          text-align: center;
        }

        .profile-picture {
          margin-right: 0;
          margin-bottom: 15px;
        }

        .stats {
          justify-content: center;
        }
      }
    </style>
  </head>
  <body class="vsc-initialized">
    <header>
      <div class="header-content">
        <a href="https://github.com/greg-randall/memento-mori" class="logo">Memento Mori</a>
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
          <div id="date-range"><?php echo "$first_timestamp - $last_timestamp"; ?></div>
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

    <!-- Script to make post data available to JavaScript -->
    <script>
    window.postData = <?php echo json_encode($post_data); ?>;
    </script>

    <!-- Include the modal JavaScript -->
    <script src="modal.js"></script>


  </body>
</html>


