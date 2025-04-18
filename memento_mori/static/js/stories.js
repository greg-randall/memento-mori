// Stories viewer functionality
document.addEventListener('DOMContentLoaded', function() {
    // Story viewer elements
    const storyViewer = document.getElementById('storyViewer');
    const storyMedia = document.getElementById('storyMedia');
    const storyCaption = document.getElementById('storyCaption');
    const storyDate = document.getElementById('storyDate');
    const storyClose = document.getElementById('storyClose');
    const storyPrev = document.getElementById('storyPrev');
    const storyNext = document.getElementById('storyNext');
    const storyProgress = document.getElementById('storyProgress');
    
    // Story data and state
    let currentStoryIndex = 0;
    let storyItems = [];
    let autoProgressTimer = null;
    const autoProgressDelay = 10000; // 10 seconds
    
    // Initialize story items from the grid
    const storyGridItems = document.querySelectorAll('.story-item');
    storyGridItems.forEach(item => {
        item.addEventListener('click', function() {
            const storyIndex = parseInt(this.getAttribute('data-index'));
            openStory(storyIndex);
        });
    });
    
    // Open a story by index
    function openStory(index) {
        // Get all story items in their current order
        storyItems = Array.from(document.querySelectorAll('.story-item'));
        currentStoryIndex = storyItems.findIndex(item => parseInt(item.getAttribute('data-index')) === index);
        
        if (currentStoryIndex === -1) return;
        
        // Show the story viewer
        storyViewer.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent scrolling
        
        // Load the current story
        loadCurrentStory();
        
        // Update URL with story info
        const timestamp = storyItems[currentStoryIndex].getAttribute('data-timestamp');
        if (timestamp) {
            const url = new URL(window.location.href);
            url.searchParams.set('story', timestamp);
            window.history.pushState({}, '', url);
        }
    }
    
    // Load the current story content
    function loadCurrentStory() {
        if (currentStoryIndex < 0 || currentStoryIndex >= storyItems.length) return;
        
        // Clear any existing timer
        clearAutoProgressTimer();
        
        const storyItem = storyItems[currentStoryIndex];
        const timestamp = storyItem.getAttribute('data-timestamp');
        const storyData = window.storiesData[timestamp];
        
        if (!storyData) return;
        
        // Reset progress bar
        storyProgress.style.width = '0%';
        
        // Update story content
        storyCaption.textContent = storyData.tt || '';
        storyDate.textContent = storyData.d || '';
        
        // Clear previous media
        storyMedia.innerHTML = '';
        
        // Ensure the story media container has the correct class
        storyMedia.className = 'story-media-container';
        
        // Create media element based on type
        const mediaUrl = storyData.m[0]; // Use first media item
        const isVideo = mediaUrl.endsWith('.mp4') || mediaUrl.endsWith('.mov') || 
                       mediaUrl.endsWith('.avi') || mediaUrl.endsWith('.webm');
        
        if (isVideo) {
            const video = document.createElement('video');
            video.src = mediaUrl;
            video.controls = true;
            video.autoplay = true;
            video.muted = false;
            video.addEventListener('play', function() {
                // Don't auto-progress for videos, let them play through
                clearAutoProgressTimer();
            });
            video.addEventListener('ended', function() {
                // Go to next story when video ends
                navigateStory(1);
            });
            storyMedia.appendChild(video);
        } else {
            const img = document.createElement('img');
            
            // Check if there's a WebP version available for non-WebP images
            if (!mediaUrl.endsWith('.webp') && 
                (mediaUrl.endsWith('.jpg') || mediaUrl.endsWith('.jpeg') || 
                 mediaUrl.endsWith('.png') || mediaUrl.endsWith('.gif'))) {
                
                // Try to use WebP version if it exists
                const webpUrl = mediaUrl.replace(/\.(jpg|jpeg|png|gif)$/i, '.webp');
                
                img.onerror = function() {
                    this.onerror = null; // Prevent infinite loop
                    this.src = mediaUrl; // Fall back to original
                };
                
                img.src = webpUrl;
            } else {
                img.src = mediaUrl;
            }
            
            img.alt = 'Story';
            storyMedia.appendChild(img);
            
            // Start auto-progress for images
            startAutoProgressTimer();
        }
        
        // Update navigation buttons visibility
        storyPrev.style.display = currentStoryIndex > 0 ? 'flex' : 'none';
        storyNext.style.display = currentStoryIndex < storyItems.length - 1 ? 'flex' : 'none';
    }
    
    // Start auto-progress timer with visual indicator
    function startAutoProgressTimer() {
        // Animate progress bar
        storyProgress.style.transition = `width ${autoProgressDelay}ms linear`;
        storyProgress.style.width = '100%';
        
        // Set timer for auto-progression
        autoProgressTimer = setTimeout(() => {
            navigateStory(1);
        }, autoProgressDelay);
    }
    
    // Clear auto-progress timer
    function clearAutoProgressTimer() {
        clearTimeout(autoProgressTimer);
        storyProgress.style.transition = 'none';
        storyProgress.style.width = '0%';
    }
    
    // Navigate to previous/next story
    function navigateStory(direction) {
        const newIndex = currentStoryIndex + direction;
        
        if (newIndex >= 0 && newIndex < storyItems.length) {
            currentStoryIndex = newIndex;
            loadCurrentStory();
            
            // Update URL
            const timestamp = storyItems[currentStoryIndex].getAttribute('data-timestamp');
            if (timestamp) {
                const url = new URL(window.location.href);
                url.searchParams.set('story', timestamp);
                window.history.pushState({}, '', url);
            }
        } else if (newIndex < 0) {
            // If trying to go before the first story, just restart current story
            loadCurrentStory();
        } else {
            // If we've reached the end, close the viewer
            closeStory();
        }
    }
    
    // Close the story viewer
    function closeStory() {
        clearAutoProgressTimer();
        storyViewer.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
        
        // Remove story parameter from URL
        const url = new URL(window.location.href);
        url.searchParams.delete('story');
        window.history.pushState({}, '', url);
    }
    
    // Event listeners
    storyClose.addEventListener('click', closeStory);
    storyPrev.addEventListener('click', () => navigateStory(-1));
    storyNext.addEventListener('click', () => navigateStory(1));
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (storyViewer.style.display !== 'none') {
            if (e.key === 'ArrowLeft') {
                navigateStory(-1);
            } else if (e.key === 'ArrowRight') {
                navigateStory(1);
            } else if (e.key === 'Escape') {
                closeStory();
            }
        }
    });
    
    // Click on the story media area to navigate forward
    storyMedia.addEventListener('click', function(e) {
        // Only if it's not a video (to avoid interfering with video controls)
        if (!e.target.matches('video')) {
            navigateStory(1);
        }
    });
    
    // Check URL for story parameter on page load
    function checkUrlForStory() {
        const urlParams = new URLSearchParams(window.location.search);
        const storyTimestamp = urlParams.get('story');
        
        if (storyTimestamp) {
            // Find the story item with this timestamp
            const storyItem = Array.from(storyGridItems).find(
                item => item.getAttribute('data-timestamp') === storyTimestamp
            );
            
            if (storyItem) {
                const storyIndex = parseInt(storyItem.getAttribute('data-index'));
                // Slight delay to ensure DOM is fully loaded
                setTimeout(() => openStory(storyIndex), 100);
            }
        }
    }
    
    // Run URL check
    checkUrlForStory();
});
