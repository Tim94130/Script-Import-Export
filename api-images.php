<?php
require('wp-load.php');
require_once( ABSPATH . 'wp-admin/includes/media.php' );
require_once( ABSPATH . 'wp-admin/includes/file.php' );
require_once( ABSPATH . 'wp-admin/includes/image.php' );

header('Content-Type: application/json');

$api_key = '12345';

// Réception des données JSON
$data = json_decode(file_get_contents('php://input'), true);

// Vérification de la clé API
if (!isset($data['api_key']) || $data['api_key'] !== $api_key) {
    echo json_encode(['error' => 'Accès refusé : clé incorrecte']);
    exit;
}

// Vérification des URLs fournies
if (!isset($data['urls']) || !is_array($data['urls'])) {
    echo json_encode(['error' => 'Aucune URL fournie']);
    exit;
}

global $wpdb;
$resultats = [];

foreach ($data['urls'] as $url) {
    // Vérifier si l'image existe déjà dans ta base
    $id = $wpdb->get_var($wpdb->prepare("SELECT ID FROM {$wpdb->prefix}posts WHERE guid = %s", $url));

    if ($id) {
        $resultats[$url] = intval($id);
    } else {
        // Sinon, importer l'image
        $image_id = media_sideload_image($url, 0, '', 'id');

        if (!is_wp_error($image_id)) {
            $resultats[$url] = intval($image_id);
        } else {
            $resultats[$url] = ['erreur' => $image_id->get_error_message()];
        }
    }
}

// Résultat final
echo json_encode($resultats);
exit;
