<?php
define('WP_USE_THEMES', false);
require_once(__DIR__ . '/wp-load.php');

header('Content-Type: application/json');
$api_key_valid = '12345';
$data = json_decode(file_get_contents('php://input'), true);

if (!isset($data['api_key']) || $data['api_key'] !== $api_key_valid) {
    echo json_encode(['error' => 'Accès refusé : clé incorrecte']);
    exit;
}

if (!isset($data['urls']) || !is_array($data['urls'])) {
    echo json_encode(['error' => 'Aucune URL fournie']);
    exit;
}

global $wpdb;
$upload_dir = wp_upload_dir();
$resultats = [];

// Fonction : retrouver l'ID d'un média à partir de son URL
function get_attachment_id_by_url($url) {
    global $wpdb;
    $upload_dir = wp_upload_dir();
    $relative_path = str_replace(trailingslashit($upload_dir['baseurl']), '', $url);

    return $wpdb->get_var($wpdb->prepare(
        "SELECT post_id FROM $wpdb->postmeta
         WHERE meta_key = '_wp_attached_file' AND meta_value = %s LIMIT 1",
        $relative_path
    ));
}

// Traitement des URLs reçues
foreach ($data['urls'] as $url) {
    $start = microtime(true);
    $id = get_attachment_id_by_url($url);
    $time_total = round(microtime(true) - $start, 4);

    if ($id) {
        $resultats[$url] = [
            'id' => intval($id),
            'note' => 'déjà présent',
            'time_total' => "{$time_total}s"
        ];
    } else {
        $resultats[$url] = [
            'erreur' => 'Fichier non trouvé dans la médiathèque',
            'time_total' => "{$time_total}s"
        ];
    }
}

echo json_encode($resultats);
exit;
