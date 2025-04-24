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

if (!isset($data['mappings']) || !is_array($data['mappings'])) {
    echo json_encode(['error' => 'Aucun mapping SKU/image_url fourni']);
    exit;
}

global $wpdb;
$upload_dir = wp_upload_dir();
$results = [];

/**
 * Retrouve l’ID d’un média depuis son URL
 */
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

/**
 * Associe une image à une variation WooCommerce
 */
function assign_image_to_variation($variation_id, $image_id) {
    if (!wp_attachment_is_image($image_id)) {
        return false;
    }
    return update_post_meta($variation_id, '_thumbnail_id', $image_id);
}

/**
 * Trouve une variation produit via son SKU
 */
function get_product_variation_by_sku($sku) {
    $product_id = wc_get_product_id_by_sku($sku);
    if (!$product_id) return null;

    $product = wc_get_product($product_id);
    return ($product && $product->is_type('variation')) ? $product : null;
}

// Traitement de chaque mapping
foreach ($data['mappings'] as $mapping) {
    $sku = isset($mapping['sku']) ? sanitize_text_field($mapping['sku']) : null;
    $image_url = isset($mapping['image_url']) ? esc_url_raw($mapping['image_url']) : null;

    if (!$sku || !$image_url) {
        $results[] = ['sku' => $sku, 'status' => 'error', 'message' => 'SKU ou URL manquant'];
        continue;
    }

    $variation = get_product_variation_by_sku($sku);
    $image_id = get_attachment_id_by_url($image_url);

    if (!$variation) {
        $results[] = ['sku' => $sku, 'status' => 'error', 'message' => 'Variation non trouvée'];
        continue;
    }

    if (!$image_id) {
        $results[] = ['sku' => $sku, 'status' => 'error', 'message' => 'Image non trouvée dans la médiathèque'];
        continue;
    }

    $success = assign_image_to_variation($variation->get_id(), $image_id);
    $results[] = [
        'sku' => $sku,
        'variation_id' => $variation->get_id(),
        'image_id' => $image_id,
        'status' => $success ? 'success' : 'error',
        'message' => $success ? 'Image assignée à la variation' : 'Erreur lors de l’assignation'
    ];
}

echo json_encode($results, JSON_PRETTY_PRINT);
exit;
