<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the
 * installation. You don't have to use the web site, you can
 * copy this file to "wp-config.php" and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * MySQL settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://codex.wordpress.org/Editing_wp-config.php
 *
 * @package WordPress
 */

// ** MySQL settings - You can get this info from your web host ** //
/** The name of the database for WordPress */
define('DB_NAME', 'yolobaytbillard');

/** MySQL database username */
define('DB_USER', 'yolobaytbillard');

/** MySQL database password */
define('DB_PASSWORD', 'Yolobb93');

/** MySQL hostname */
define('DB_HOST', 'yolobaytbillard.mysql.db:3306');

/** Database Charset to use in creating database tables. */
define('DB_CHARSET', 'utf8');

/** The Database Collate type. Don't change this if in doubt. */
define('DB_COLLATE', '');

/**#@+
 * Authentication Unique Keys and Salts.
 *
 * Change these to different unique phrases!
 * You can generate these using the {@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}
 * You can change these at any point in time to invalidate all existing cookies. This will force all users to have to log in again.
 *
 * @since 2.6.0
 */
define('AUTH_KEY',         'lVsRJS8aK2niF3BNpcpysJxFa0DmVypBygG8cLHHr+sWbAyfqVuKwA4IgUfL');
define('SECURE_AUTH_KEY',  'lkZPMaTeK/O2Ct5YTe47CQrcHl9aBo+UxAk0NxjxnZ2l18GWAhYiybCELcjv');
define('LOGGED_IN_KEY',    'YVYzvNvPoahF1ISW/reHy10CgiFmpzvKYDHGGEbOZdW8wIWjeiICWoyoUQIM');
define('NONCE_KEY',        'JWYg/os/7J4tYAaXoT2CQqlpk3PZK1/BNSMqU9TfbK4XY7N41DMOG3AXjwWr');
define('AUTH_SALT',        't2Fhwrx45WCjZ1I4zFm7gEH2oZV0GULmGvRb4afUFsm3P07x9Xtnr0aiE5QH');
define('SECURE_AUTH_SALT', 'yDoGHElntZHb0uS6lgdt0RquzdTxtDVcOuuTLJnpZFPnKC/gwd6EaYp9+PNS');
define('LOGGED_IN_SALT',   'HvJeKe0UQSKObsOS0igWHdtNW3tOt+x9aPqDm4mwKkpX4Fcr9bCiCvkjRHTd');
define('NONCE_SALT',       'pyeBpMEQOVY+i6Wzw58XIeDK+keUMlcM2Ar4sX19wQuAmTibEdqWyK/RRCTu');

/**#@-*/

/**
 * WordPress Database Table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix  = 'wor1726_';

/**
 * For developers: WordPress debugging mode.
 *
 * Change this to true to enable the display of notices during development.
 * It is strongly recommended that plugin and theme developers use WP_DEBUG
 * in their development environments.
 *
 * For information on other constants that can be used for debugging,
 * visit the Codex.
 *
 * @link https://codex.wordpress.org/Debugging_in_WordPress
 */
// Active le mode debug
define( 'WP_DEBUG', true );                

// Envoie les erreurs PHP dans debug.log
define( 'WP_DEBUG_LOG', true );           

// N’affiche pas les erreurs à l’écran (sécurise la prod)
define( 'WP_DEBUG_DISPLAY', false );      
@ini_set( 'display_errors', 0 );

define( 'UPLOADS', 'wp-content/uploads/image-site' );


/* That's all, stop editing! Happy blogging. */
@ini_set('upload_max_filesize', '20000M');
@ini_set('post_max_size', '20000M');
@ini_set('memory_limit', '512M');
@ini_set('max_execution_time', '1200');
@ini_set('max_input_time', '1200');

/** Absolute path to the WordPress directory. */
if ( !defined('ABSPATH') )
	define('ABSPATH', dirname(__FILE__) . '/');

/* Fixes "Add media button not working", see http://www.carnfieldwebdesign.co.uk/blog/wordpress-fix-add-media-button-not-working/ */
define('CONCATENATE_SCRIPTS', false );

/** Sets up WordPress vars and included files. */
require_once(ABSPATH . 'wp-settings.php');
