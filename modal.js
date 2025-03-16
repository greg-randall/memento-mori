document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const postsGrid = document.getElementById('postsGrid');
    const postModal = document.getElementById('postModal');
    const closeModalBtn = document.getElementById('closeModal');
    const modalPrev = document.getElementById('modalPrev');
    const modalNext = document.getElementById('modalNext');
    const postMedia = document.getElementById('postMedia');
    const postCaption = document.getElementById('postCaption');
    const postStats = document.getElementById('postStats');
    const postDate = document.getElementById('postDate');
    const postUsername = document.getElementById('postUsername');
    const postUserPic = document.getElementById('postUserPic');
    
    // Global variables to track current post and indexes
    let currentPostIndex = -1;
    let postIndexToTimestamp = {}; // Map post index to timestamp
    
    // Initialize by creating mapping and attaching listeners
    function initialize() {
        // Create a mapping from post_index to timestamp
        Object.entries(window.postData).forEach(([timestamp, post]) => {
            postIndexToTimestamp[post.post_index] = timestamp;
        });
        
        // Attach click listeners to grid items
        attachGridItemListeners();
    }
    
    // Attach click event listeners to all grid items
    function attachGridItemListeners() {
        const gridItems = document.querySelectorAll('.grid-item');
        gridItems.forEach(item => {
            item.addEventListener('click', function() {
                const postIndex = parseInt(this.getAttribute('data-index'));
                openModal(postIndex);
            });
        });
    }
    
    // Open the modal with the selected post
  // Replace the openModal function with this updated version
function openModal(index) {
    currentPostIndex = index;
    
    // Get the timestamp using the post_index mapping
    const timestamp = postIndexToTimestamp[index];
    
    // Get the post data using the timestamp
    const post = window.postData[timestamp];
    
    // Show the modal first (important for correct dimensions)
    postModal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent scrolling
    
    // Update modal content
    updateModalContent(post);
    
    // For mobile devices, ensure content is visible and properly sized
    if (window.innerWidth <= 768) {
        window.scrollTo(0, 0);
        postModal.scrollTop = 0;
        
        // Force layout recalculation with a longer timeout
        setTimeout(() => {
            const mediaContainer = document.querySelector('.media-container');
            const postMediaEl = document.getElementById('postMedia');
            
            // Ensure post-media has explicit height
            if (postMediaEl) {
                postMediaEl.style.height = '50vh';
                postMediaEl.style.minHeight = '300px';
            }
            
            // Ensure media-container has explicit height
            if (mediaContainer) {
                mediaContainer.style.height = '100%';
                mediaContainer.style.display = 'flex';
                
                // Force reflow
                void mediaContainer.offsetHeight;
            }
            
            // Reset any active slides to ensure they're visible
            const activeSlides = document.querySelectorAll('.media-slide.active');
            activeSlides.forEach(slide => {
                slide.style.opacity = '0';
                void slide.offsetHeight; // Force reflow
                slide.style.opacity = '1';
                
                // Make sure images have height
                const img = slide.querySelector('img');
                if (img) {
                    img.style.maxHeight = '100%';
                    img.style.width = 'auto';
                    img.style.height = 'auto';
                }
            });
        }, 50); // Increase timeout for more reliability
    }
}
    //Creates the appropriate media element (video or image) based on the file type
    function createMediaElement(mediaUrl) {
        // Check if the media is a video based on file extension
        if (mediaUrl.endsWith('.mp4') || mediaUrl.endsWith('.mov') || 
            mediaUrl.endsWith('.avi') || mediaUrl.endsWith('.webm')) {
            
            // Create video element
            const video = document.createElement('video');
            video.src = mediaUrl;
            video.controls = true;
            video.autoplay = true;
            video.loop = true;
            video.muted = false;
            video.playsInline = true;
            video.alt = 'Instagram video post';
            
            return video;
        } else {
            // Create image element
            const img = document.createElement('img');
            img.src = mediaUrl;
            img.alt = 'Instagram post';
            
            return img;
        }
    }
    // Update the modal content with the post data
    function updateModalContent(post) {
        // Clear previous content
        postMedia.innerHTML = '';
        postCaption.innerHTML = '';
        postStats.innerHTML = '';
        
        // Create media container for the slides
        const mediaContainer = document.createElement('div');
        mediaContainer.className = 'media-container';
        
        // Check if the post has multiple media
        if (post.media && post.media.length > 1) {
            // Create slides for each media item
            post.media.forEach((mediaUrl, index) => {
                const slide = document.createElement('div');
                slide.className = `media-slide ${index === 0 ? 'active' : ''}`;
                
                // Create and add the appropriate media element
                const mediaElement = createMediaElement(mediaUrl);
                slide.appendChild(mediaElement);
                
                mediaContainer.appendChild(slide);
            });
            
            // Add navigation buttons for slideshow
            const prevBtn = document.createElement('div');
            prevBtn.className = 'slideshow-nav slideshow-prev';
            prevBtn.innerHTML = '❮';
            prevBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                navigateSlideshow(-1);
            });
            
            const nextBtn = document.createElement('div');
            nextBtn.className = 'slideshow-nav slideshow-next';
            nextBtn.innerHTML = '❯';
            nextBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                navigateSlideshow(1);
            });
            
            // Add indicator dots
            const indicator = document.createElement('div');
            indicator.className = 'slideshow-indicator';
            
            for (let i = 0; i < post.media.length; i++) {
                const dot = document.createElement('div');
                dot.className = `slideshow-dot ${i === 0 ? 'active' : ''}`;
                dot.setAttribute('data-index', i);
                dot.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.getAttribute('data-index'));
                    showSlide(index);
                });
                indicator.appendChild(dot);
            }
            
            mediaContainer.appendChild(prevBtn);
            mediaContainer.appendChild(nextBtn);
            mediaContainer.appendChild(indicator);
        } else {
            // Single media post
            const slide = document.createElement('div');
            slide.className = 'media-slide active';
            
            // Create and add the appropriate media element
            const mediaElement = createMediaElement(post.media[0]);
            slide.appendChild(mediaElement);
            
            mediaContainer.appendChild(slide);
        }
        
        postMedia.appendChild(mediaContainer);
        
        // Set post caption
        postCaption.textContent = post.title || '';
        
        // Set post stats
        if (post.Impressions) {
            const impressionsDiv = document.createElement('div');
            impressionsDiv.className = 'post-stat';
            impressionsDiv.innerHTML = `
                <span class="post-stat-icon">👁️</span>
                <span>${post.Impressions} views</span>
            `;
            postStats.appendChild(impressionsDiv);
        }
        
        if (post.Likes) {
            const likesDiv = document.createElement('div');
            likesDiv.className = 'post-stat';
            likesDiv.innerHTML = `
                <span class="post-stat-icon">♥</span>
                <span>${post.Likes} likes</span>
            `;
            postStats.appendChild(likesDiv);
        }
        
        if (post.Comments) {
            const commentsDiv = document.createElement('div');
            commentsDiv.className = 'post-stat';
            commentsDiv.innerHTML = `
                <span class="post-stat-icon">💬</span>
                <span>${post.Comments} comments</span>
            `;
            postStats.appendChild(commentsDiv);
        }
        
        // Set post date
        postDate.textContent = post.creation_timestamp_readable;
        
        // Show/hide stats container based on whether there are any stats
        postStats.style.display = postStats.children.length > 0 ? 'flex' : 'none';
    }
    
    // Navigate between slides in a multi-media post
    function navigateSlideshow(direction) {
        const slides = document.querySelectorAll('.media-slide');
        const dots = document.querySelectorAll('.slideshow-dot');
        let activeIndex = 0;
        
        // Find the currently active slide
        slides.forEach((slide, index) => {
            if (slide.classList.contains('active')) {
                activeIndex = index;
            }
        });
        
        // Calculate the new index
        let newIndex = activeIndex + direction;
        if (newIndex < 0) newIndex = slides.length - 1;
        if (newIndex >= slides.length) newIndex = 0;
        
        // Update slides and dots
        showSlide(newIndex);
    }
    
    // Show a specific slide
    function showSlide(index) {
        const slides = document.querySelectorAll('.media-slide');
        const dots = document.querySelectorAll('.slideshow-dot');
        
        // Remove active class from all slides and dots
        slides.forEach(slide => slide.classList.remove('active'));
        if (dots.length > 0) {
            dots.forEach(dot => dot.classList.remove('active'));
            dots[index].classList.add('active');
        }
        
        // Add active class to the selected slide
        slides[index].classList.add('active');
    }
    
    // Navigate between posts (next/prev buttons in modal)
    function navigatePost(direction) {
        // Get all post indexes in sorted order
        const postIndexes = Object.keys(postIndexToTimestamp).map(Number).sort((a, b) => a - b);
        
        // Find current index position in the array
        const currentPosition = postIndexes.indexOf(currentPostIndex);
        
        // Calculate new position with wraparound
        let newPosition = (currentPosition + direction + postIndexes.length) % postIndexes.length;
        
        // Get the new post index
        const newPostIndex = postIndexes[newPosition];
        
        // Open the new post
        openModal(newPostIndex);
    }
    
    // Close the modal
    function closeModal() {
        postModal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Re-enable scrolling
    }
    
    // Event listeners for modal navigation
    closeModalBtn.addEventListener('click', closeModal);
    modalPrev.addEventListener('click', function(e) {
        e.stopPropagation();
        navigatePost(-1);
    });
    modalNext.addEventListener('click', function(e) {
        e.stopPropagation();
        navigatePost(1);
    });
    
    // Close modal when clicking outside of content
    postModal.addEventListener('click', function(e) {
        if (e.target === postModal) {
            closeModal();
        }
    });
    
    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (postModal.style.display === 'block') {
            if (e.key === 'Escape') {
                closeModal();
            } else if (e.key === 'ArrowLeft') {
                navigatePost(-1);
            } else if (e.key === 'ArrowRight') {
                navigatePost(1);
            }
        }
    });
    
    // Initialize the modal functionality
    if (typeof window.postData !== 'undefined') {
        initialize();
    } else {
        console.error('Post data not available');
    }
});
