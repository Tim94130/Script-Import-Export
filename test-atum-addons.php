<?php
header('Content-Type: text/plain');

$url = 'https://stockmanagementlabs.com/wp-json/atum/v1/addons';

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_USERAGENT, 'ATUM/1.0');

// Ajout d’un timeout plus court pour éviter que ça bloque longtemps
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5); // max 5 sec pour connexion
curl_setopt($ch, CURLOPT_TIMEOUT, 10);       // max 10 sec pour tout

$response = curl_exec($ch);
$error = curl_error($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response && $http_code === 200) {
    echo "✅ Réponse OK :\n";
    echo $response;
} else {
    echo "❌ Erreur cURL : $error\n";
    echo "Code HTTP : $http_code\n";
}
