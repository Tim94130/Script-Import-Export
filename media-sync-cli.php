<?php
/**
 * Plugin Name: WP-CLI Media Sync
 * Description: Commande WP-CLI pour importer des fichiers du dossier image-site dans la médiathèque.
 */

if (defined('WP_CLI') && WP_CLI) {
    class Media_Sync_CLI {
        /**
         * Lance la synchronisation de tous les fichiers.
         *
         * ## EXAMPLES
         * wp media-sync
         */
        public function __invoke($args, $assoc_args) {
            $folder = 'wp-content/uploads/image-site';
            $abs_folder = ABSPATH . $folder;
            $upload_dir = wp_upload_dir();

            if (!is_dir($abs_folder)) {
                WP_CLI::error("Le dossier $folder n'existe pas.");
                return;
            }

            $files = new RecursiveIteratorIterator(
                new RecursiveDirectoryIterator($abs_folder),
                RecursiveIteratorIterator::LEAVES_ONLY
            );

            $count = 0;
            $skipped = 0;

            global $wpdb;

            foreach ($files as $file) {
                if (!$file->isFile()) continue;

                $full_path = $file->getPathname();
                $relative_to_uploads = ltrim(str_replace(trailingslashit($upload_dir['basedir']), '', $full_path), '/');

                $exists = $wpdb->get_var($wpdb->prepare(
                    "SELECT post_id FROM $wpdb->postmeta WHERE meta_key = '_wp_attached_file' AND meta_value = %s",
                    $relative_to_uploads
                ));

                if ($exists) {
                    $skipped++;
                    continue;
                }

                $filename = basename($full_path);
                $filetype = wp_check_filetype($filename, null);

                $attachment = [
                    'guid'           => $upload_dir['baseurl'] . '/' . $relative_to_uploads,
                    'post_mime_type' => $filetype['type'],
                    'post_title'     => sanitize_file_name(pathinfo($filename, PATHINFO_FILENAME)),
                    'post_content'   => '',
                    'post_status'    => 'inherit'
                ];

                $attach_id = wp_insert_attachment($attachment, $full_path);
                //$attach_data = wp_generate_attachment_metadata($attach_id, $full_path);
                //wp_update_attachment_metadata($attach_id, $attach_data);

                WP_CLI::log("✅ $relative_to_uploads (ID $attach_id)");
                $count++;
            }

            WP_CLI::success("🎉 Import terminé. $count fichiers ajoutés, $skipped déjà présents.");
        }
    }

    WP_CLI::add_command('media-sync', 'Media_Sync_CLI');
}
