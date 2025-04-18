// memento_mori/static/js/modal.js
document.addEventListener('DOMContentLoaded', function () {
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
    const sortLinks = document.querySelectorAll('.sort-link');

    // Global variables to track current post and indexes
    let currentPostIndex = -1;
    let currentSlideIndex = 0;
    let postIndexToTimestamp = {}; // Map post index to timestamp
    let currentSortType = 'newest'; // Default sort

    // Initialize by creating mapping and attaching listeners
    function initialize() {
        // Create a mapping from post index to timestamp
        Object.entries(window.postData).forEach(([timestamp, post]) => {
            postIndexToTimestamp[post.i] = timestamp;
        });

        // Attach click listeners to grid items
        attachGridItemListeners();

        // Initialize sorting functionality
        initializeSorting();
    }

    // Initialize sorting functionality
    function initializeSorting() {
        // Add event listeners to sort links
        sortLinks.forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();

                // Update active class
                sortLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');

                // Get sort type and sort posts
                const sortType = this.getAttribute('data-sort');
                currentSortType = sortType;
                sortPosts(sortType);
            });
        });
    }

    // Sort posts based on selected criteria
    function sortPosts(sortType) {
        // Get all grid items
        let gridItems = Array.from(document.querySelectorAll('.grid-item'));

        // Sort the grid items based on the selected criteria
        switch (sortType) {
            case 'newest':
                // Sort by timestamp (newest first) - this is the default
                gridItems.sort((a, b) => {
                    const indexA = parseInt(a.getAttribute('data-index'));
                    const indexB = parseInt(b.getAttribute('data-index'));
                    const timestampA = getTimestampByIndex(indexA);
                    const timestampB = getTimestampByIndex(indexB);
                    return timestampB - timestampA;
                });
                break;

            case 'oldest':
                // Sort by timestamp (oldest first)
                gridItems.sort((a, b) => {
                    const indexA = parseInt(a.getAttribute('data-index'));
                    const indexB = parseInt(b.getAttribute('data-index'));
                    const timestampA = getTimestampByIndex(indexA);
                    const timestampB = getTimestampByIndex(indexB);
                    return timestampA - timestampB;
                });
                break;

            case 'most-likes':
                // Sort by number of likes
                gridItems.sort((a, b) => {
                    const indexA = parseInt(a.getAttribute('data-index'));
                    const indexB = parseInt(b.getAttribute('data-index'));
                    const likesA = getLikesByIndex(indexA) || 0;
                    const likesB = getLikesByIndex(indexB) || 0;
                    return likesB - likesA;
                });
                break;

            case 'most-comments':
                // Sort by number of comments
                gridItems.sort((a, b) => {
                    const indexA = parseInt(a.getAttribute('data-index'));
                    const indexB = parseInt(b.getAttribute('data-index'));
                    const commentsA = getCommentsByIndex(indexA) || 0;
                    const commentsB = getCommentsByIndex(indexB) || 0;
                    return commentsB - commentsA;
                });
                break;

            case 'most-views':
                // Sort by number of views/impressions
                gridItems.sort((a, b) => {
                    const indexA = parseInt(a.getAttribute('data-index'));
                    const indexB = parseInt(b.getAttribute('data-index'));
                    const viewsA = getViewsByIndex(indexA) || 0;
                    const viewsB = getViewsByIndex(indexB) || 0;
                    return viewsB - viewsA;
                });
                break;

            case 'random':
                // Shuffle the grid items randomly
                gridItems.sort(() => Math.random() - 0.5);
                break;
        }

        // Reorder the grid items in the DOM
        const fragment = document.createDocumentFragment();
        gridItems.forEach(item => {
            fragment.appendChild(item);
        });

        // Clear the grid and append the sorted items
        postsGrid.innerHTML = '';
        postsGrid.appendChild(fragment);

        // Reattach event listeners to grid items
        attachGridItemListeners();
    }

    // Helper function to get timestamp by post index
    function getTimestampByIndex(index) {
        const timestamp = postIndexToTimestamp[index];
        return parseInt(timestamp);
    }

    // Helper function to get likes by post index
    function getLikesByIndex(index) {
        const timestamp = postIndexToTimestamp[index];
        if (timestamp && window.postData[timestamp]) {
            return parseInt(window.postData[timestamp].l) || 0;
        }
        return 0;
    }

    // Helper function to get comments by post index
    function getCommentsByIndex(index) {
        const timestamp = postIndexToTimestamp[index];
        if (timestamp && window.postData[timestamp]) {
            return parseInt(window.postData[timestamp].c) || 0;
        }
        return 0;
    }

    // Helper function to get views/impressions by post index
    function getViewsByIndex(index) {
        const timestamp = postIndexToTimestamp[index];
        if (timestamp && window.postData[timestamp]) {
            return parseInt(window.postData[timestamp].im) || 0;
        }
        return 0;
    }

    // Attach click event listeners to all grid items
    function attachGridItemListeners() {
        const gridItems = document.querySelectorAll('.grid-item');
        gridItems.forEach(item => {
            item.addEventListener('click', function () {
                const postIndex = parseInt(this.getAttribute('data-index'));
                openModal(postIndex);
            });
        });
    }

    // Open the modal with the selected post
    function openModal(index, imageIndex = 0) {
        currentPostIndex = index;

        // Store the current scroll position before opening the modal
        const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;

        // Get the timestamp using the post_index mapping
        const timestamp = postIndexToTimestamp[index];

        // Get the post data using the timestamp
        const post = window.postData[timestamp];

        // Show the modal first (important for correct dimensions)
        postModal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent scrolling

        // Store the scroll position as a data attribute on the modal
        postModal.setAttribute('data-scroll-position', scrollPosition);

        // Update modal content
        updateModalContent(post, imageIndex);

        // Update URL with post ID and image index
        updateUrlWithPostInfo(timestamp, imageIndex);

        // For mobile devices, ensure content is visible and properly sized
        if (window.innerWidth <= 768) {
            // Don't scroll to top on mobile as it causes the issue
            // Instead, just ensure the modal is properly positioned
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

    // Function to update the URL with post and image information
    function updateUrlWithPostInfo(timestamp, imageIndex) {
        // Create a new URL object based on the current URL
        const url = new URL(window.location.href);

        // Set the post parameter to the timestamp
        url.searchParams.set('post', timestamp);

        // Only add the image parameter if it's not the first image
        if (imageIndex > 0) {
            url.searchParams.set('image', imageIndex);
        } else {
            url.searchParams.delete('image');
        }

        // Update the browser history without reloading the page
        window.history.pushState({}, '', url);
    }
    // Creates the appropriate media element (video or image) based on the file type
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

            // Check if there's a WebP version available for non-WebP images
            if (!mediaUrl.endsWith('.webp') &&
                (mediaUrl.endsWith('.jpg') || mediaUrl.endsWith('.jpeg') ||
                    mediaUrl.endsWith('.png') || mediaUrl.endsWith('.gif'))) {

                // Try to use WebP version if it exists
                const webpUrl = mediaUrl.replace(/\.(jpg|jpeg|png|gif)$/i, '.webp');

                // Set up error handling to fall back to original if WebP doesn't exist
                img.onerror = function () {
                    this.onerror = null; // Prevent infinite loop
                    this.src = mediaUrl; // Fall back to original
                };

                img.src = webpUrl;
            } else {
                img.src = mediaUrl;
            }

            img.alt = 'Instagram post';

            return img;
        }
    }
    // Update modal content with the post data
    function updateModalContent(post, initialImageIndex = 0) {
        // Clear previous content
        postMedia.innerHTML = '';
        postCaption.innerHTML = '';
        postStats.innerHTML = '';

        // Create media container for the slides
        const mediaContainer = document.createElement('div');
        mediaContainer.className = 'media-container';

        // Check if the post has multiple media
        if (post.m && post.m.length > 1) {  // Changed from media
            // Create slides for each media item
            post.m.forEach((mediaUrl, index) => {  // Changed from media
                const slide = document.createElement('div');
                slide.className = `media-slide ${index === initialImageIndex ? 'active' : ''}`;

                // Create and add the appropriate media element
                const mediaElement = createMediaElement(mediaUrl);
                slide.appendChild(mediaElement);

                mediaContainer.appendChild(slide);
            });

            // Add navigation buttons for slideshow
            const prevBtn = document.createElement('div');
            prevBtn.className = 'slideshow-nav slideshow-prev';
            prevBtn.innerHTML = '❮';
            prevBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                navigateSlideshow(-1);
            });

            const nextBtn = document.createElement('div');
            nextBtn.className = 'slideshow-nav slideshow-next';
            nextBtn.innerHTML = '❯';
            nextBtn.addEventListener('click', function (e) {
                e.stopPropagation();
                navigateSlideshow(1);
            });

            // Add indicator dots
            const indicator = document.createElement('div');
            indicator.className = 'slideshow-indicator';

            for (let i = 0; i < post.m.length; i++) {
                const dot = document.createElement('div');
                dot.className = `slideshow-dot ${i === initialImageIndex ? 'active' : ''}`;
                dot.setAttribute('data-index', i);
                dot.addEventListener('click', function (e) {
                    e.stopPropagation();
                    const index = parseInt(this.getAttribute('data-index'));
                    showSlide(index);
                });
                indicator.appendChild(dot);
            }

            mediaContainer.appendChild(prevBtn);
            mediaContainer.appendChild(nextBtn);
            mediaContainer.appendChild(indicator);

            // Set the current slide index to the initial image index
            currentSlideIndex = initialImageIndex;
        } else {
            // Single media post
            const slide = document.createElement('div');
            slide.className = 'media-slide active';

            // Create and add the appropriate media element
            const mediaElement = createMediaElement(post.m[0]);  // Changed from media
            slide.appendChild(mediaElement);

            mediaContainer.appendChild(slide);
        }

        postMedia.appendChild(mediaContainer);

        // Set post caption
        if (post.tt) {
            postCaption.innerHTML = post.tt.replace(/\n/g, '<br>');
        } else {
            postCaption.innerHTML = '';
        }

        // Set post stats
        if (post.im) {
            const impressionsDiv = document.createElement('div');
            impressionsDiv.className = 'post-stat';
            impressionsDiv.innerHTML = `
                <span class="post-stat-icon">👁️</span>
                <span>${post.im} views</span>
            `;
            postStats.appendChild(impressionsDiv);
        }

        if (post.l) {
            const likesDiv = document.createElement('div');
            likesDiv.className = 'post-stat';
            likesDiv.innerHTML = `
                <span class="post-stat-icon">♥</span>
                <span>${post.l}</span>
            `;
            postStats.appendChild(likesDiv);
        }

        if (post.c) {
            const commentsDiv = document.createElement('div');
            commentsDiv.className = 'post-stat';
            commentsDiv.innerHTML = `
                <span class="post-stat-icon">💬</span>
                <span>${post.c} comments</span>
            `;
            postStats.appendChild(commentsDiv);
        }

        // Set post date
        postDate.textContent = post.d;

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

        // Pause any videos in the current slide
        const currentVideo = slides[activeIndex].querySelector('video');
        if (currentVideo) {
            currentVideo.pause();
        }

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

        // Pause all videos before changing slides
        slides.forEach(slide => {
            const video = slide.querySelector('video');
            if (video) {
                video.pause();
            }
        });

        // Remove active class from all slides and dots
        slides.forEach(slide => slide.classList.remove('active'));
        if (dots.length > 0) {
            dots.forEach(dot => dot.classList.remove('active'));
            dots[index].classList.add('active');
        }

        // Add active class to the selected slide
        slides[index].classList.add('active');

        // Update current slide index
        currentSlideIndex = index;

        // Update URL with the new image index
        const timestamp = postIndexToTimestamp[currentPostIndex];
        updateUrlWithPostInfo(timestamp, index);
    }

    // Navigate between posts (next/prev buttons in modal)
    function navigatePost(direction) {
        // Pause all videos in the current post
        const videos = document.querySelectorAll('.media-slide video');
        videos.forEach(video => {
            if (video) {
                video.pause();
            }
        });

        // Get all grid items in their current sorted order
        const gridItems = Array.from(document.querySelectorAll('.grid-item'));
        const gridIndexes = gridItems.map(item => parseInt(item.getAttribute('data-index')));

        // Find the position of the current post in the sorted grid
        const currentPosition = gridIndexes.indexOf(currentPostIndex);

        if (currentPosition === -1) {
            console.error('Current post not found in grid');
            return;
        }

        // Calculate new position with wraparound
        let newPosition = (currentPosition + direction + gridIndexes.length) % gridIndexes.length;

        // Get the new post index from the grid's current order
        const newPostIndex = gridIndexes[newPosition];

        // Open the new post
        openModal(newPostIndex);
    }

    // Close the modal
    function closeModal() {
        // Pause all videos before closing the modal
        const videos = document.querySelectorAll('.media-slide video');
        videos.forEach(video => {
            if (video) {
                video.pause();
            }
        });

        // Store the current scroll position before closing the modal
        const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;

        postModal.style.display = 'none';
        document.body.style.overflow = 'auto'; // Re-enable scrolling

        // Remove post and image parameters from URL
        const url = new URL(window.location.href);
        url.searchParams.delete('post');
        url.searchParams.delete('image');
        window.history.pushState({}, '', url);

        // Restore the scroll position after a short delay
        setTimeout(() => {
            window.scrollTo({
                top: scrollPosition,
                behavior: 'auto' // Use 'auto' instead of 'smooth' to prevent visible scrolling
            });
        }, 10);
    }

    // Event listeners for modal navigation
    closeModalBtn.addEventListener('click', closeModal);
    modalPrev.addEventListener('click', function (e) {
        e.stopPropagation();
        navigatePost(-1);
    });
    modalNext.addEventListener('click', function (e) {
        e.stopPropagation();
        navigatePost(1);
    });

    // Close modal when clicking outside of content
    postModal.addEventListener('click', function (e) {
        if (e.target === postModal) {
            closeModal();
        }
    });

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
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

        // Check if URL has post and image parameters
        const urlParams = new URLSearchParams(window.location.search);
        const postTimestamp = urlParams.get('post');
        const imageIndex = parseInt(urlParams.get('image') || '0');

        if (postTimestamp && window.postData[postTimestamp]) {
            // Find the post index from the timestamp
            let postIndex = -1;
            Object.entries(postIndexToTimestamp).forEach(([index, timestamp]) => {
                if (timestamp === postTimestamp) {
                    postIndex = parseInt(index);
                }
            });

            if (postIndex >= 0) {
                // Open the modal with the specified post and image
                setTimeout(() => {
                    openModal(postIndex, imageIndex);
                }, 500); // Delay to ensure everything is loaded
            }
        }
    } else {
        console.error('Post data not available');
    }
});





/**
 * Fixes common Unicode encoding issues in text
 * @param {string} text - The text to fix
 * @return {string} - The fixed text
 */
function fixEncodingIssues(text) {
    if (!text) return text;
    
    // Common replacements for incorrectly encoded characters
    const replacements = [
      // Fix smart quotes and apostrophes
      { pattern: /â\u0080\u0099/g, replacement: "\u2019" },  // Right single quote/apostrophe
      { pattern: /â\u0080\u009c/g, replacement: "\u201C" },  // Left double quote
      { pattern: /â\u0080\u009d/g, replacement: "\u201D" },  // Right double quote
      { pattern: /â\u0080\u0098/g, replacement: "\u2018" },  // Left single quote
      
      // Fix dashes and ellipsis
      { pattern: /â\u0080\u0093/g, replacement: "\u2013" },  // En dash
      { pattern: /â\u0080\u0094/g, replacement: "\u2014" },  // Em dash
      { pattern: /â\u0080¦/g,   replacement: "\u2026" },      // Ellipsis
      
      // Remove non-breaking space indicator
      { pattern: /Â/g, replacement: "" },
      
      // Fix fractions
      { pattern: /Â½/g, replacement: "\u00BD" },             // Half fraction
  
      // Fix bullet point
      { pattern: /â€¢/g, replacement: "•" },
  
      // Fix common mis-encoded accented characters
      { pattern: /Ã©/g, replacement: "é" },
      { pattern: /Ã¨/g, replacement: "è" },
      { pattern: /Ã¢/g, replacement: "â" },
      { pattern: /Ãª/g, replacement: "ê" },
      { pattern: /Ã«/g, replacement: "ë" },
      { pattern: /Ã®/g, replacement: "î" },
      { pattern: /Ã¯/g, replacement: "ï" },
      { pattern: /Ã´/g, replacement: "ô" },
      { pattern: /Ã¶/g, replacement: "ö" },
      { pattern: /Ã¹/g, replacement: "ù" },
      { pattern: /Ãº/g, replacement: "ú" },
      { pattern: /Ã¼/g, replacement: "ü" },
      { pattern: /Ã§/g, replacement: "ç" }
    ];
    
    // Apply all replacements
    let fixedText = text;
    for (const { pattern, replacement } of replacements) {
      fixedText = fixedText.replace(pattern, replacement);
    }
  
    return fixedText;
  }
    
  // Apply the fix to all post captions when the page loads
  document.addEventListener('DOMContentLoaded', function() {
    // Fix the JSON data directly
    for (const timestamp in window.postData) {
      const post = window.postData[timestamp];
      if (post.tt) {  // Changed from title
        post.tt = fixEncodingIssues(post.tt);  // Changed from title
      }
    }
    
    // Update any already rendered content
    const captions = document.querySelectorAll('.post-caption');
    captions.forEach(caption => {
      caption.textContent = fixEncodingIssues(caption.textContent);
    });
  });
  
