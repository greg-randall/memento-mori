<?php
/**
 * Generate a static site from the Instagram data
 * This script can be run from the command line to generate the static site
 * without serving it through PHP's web server
 */

// Suppress HTML output
ob_start();

// Include the main index.php file which will generate the static site
include('index.php');

// Clear the output buffer
ob_end_clean();

echo "Static site generation complete!\n";
echo "The site has been generated in the 'distribution' folder.\n";
echo "You can view it by opening distribution/index.html in your browser.\n";
?>
