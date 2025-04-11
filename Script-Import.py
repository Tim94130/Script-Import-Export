# Importation des bibliothèques nécessaires
import pandas as pd
from tkinter import Tk, filedialog
import os
import re
import json
import requests
from time import sleep
import unicodedata
from collections import defaultdict
from rapidfuzz import process, fuzz  # Si nécessaireimport csv
import csv
import MySQLdb


# Définitions globales pour la détection des couleurs
adjectifs_ignores = [
    "dark", "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent"
]

couleurs_base = [
    "white", "black", "brown", "blue", "red", "pink", "green", 
    "grey", "gray", "yellow", "orange", "purple", "violet",
    "beige", "gold", "silver", "taupe", "cyan", "magenta",
    "navy", "maroon", "lime", "olive", "teal", "aqua",
    "blanc", "noir", "marron", "brun", "bleu", "rouge", "rose", 
    "vert", "gris", "jaune", "violet", "beige", "doré", "argent", "kaki",
    "turquoise", "fuchsia", "lavande", "ocre", "ivory", "ivoires", "argenté",
    "rose gold", "off white", "peach pink", "sepia black", "golden",
    "sable", "chocolat", "prune" ,"dark brown"
]

mapping_couleurs = {
    "white": "Blanc",
    "off white": "Blanc cassé",
    "ivory": "Blanc cassé",
    "blanc": "Blanc",
    "dark brown": "Marron",
    "black": "Noir",
    "noir": "Noir",
    "sepia black": "Noir",
    
    "brown": "Marron",
    "brun": "Marron",
    "marron": "Marron",
    "chocolat": "Marron",
    
    "red": "Rouge",
    "rouge": "Rouge",
    
    "pink": "Rose",
    "rose": "Rose",
    "peach pink": "Rose",
    
    "green": "Vert",
    "vert": "Vert",
    "leaf green": "Vert",
    
    "grey": "Gris",
    "gray": "Gris",
    "gris": "Gris",
    "mirage grey": "Gris",
    
    "yellow": "Jaune",
    "jaune": "Jaune",
    
    "orange": "Orange",
    
    "purple": "Violet",
    "violet": "Violet",
    "lavande": "Violet",
    "prune": "Violet",
    
    "beige": "Beige",
    "sable": "Beige",
    "taupe": "Taupe",
    
    "gold": "Doré",
    "golden": "Doré",
    "rose gold": "Rose Gold",
    
    "silver": "Argent",
    "argent": "Argent",
    "argenté": "Argent",
    
    "kaki": "Kaki",
    
    "fuchsia": "Fuchsia",
    "magenta": "Fuchsia",
    
    "blue": "Bleu",
    "bleu": "Bleu",
    "navy": "Bleu marine",
    "cyan": "Cyan",
    "aqua": "Cyan",
    "turquoise": "Turquoise",
    
    "maroon": "Bordeaux",
    "bordeaux": "Bordeaux",
    
    "lime": "Vert clair",
    "olive": "Vert olive",
    
    "teal": "Bleu-vert"
}



############################################
# Fonctions de transformation du CSV
############################################

def renommer_colonnes_pour_woocommerce(df):
    correspondance_woocommerce = {
        "Référence": "SKU",
        "Nom de l'article (en Français)": "Name",
        "Description courte (en Français)": "Short description",
        "Description (en Français)": "Description",
        "Prix pour le groupe Défaut": "Regular price",
        "Stock - Quantité": "Stock",
        "Option Couleur (en Français)": "Attribute 1 value(s)",
        "Option Taille (en Français)": "Attribute 2 value(s)",
        "Poids (en Kg)": "Weight (kg)",
        "Longueur (en cm)": "Length (cm)",
        "Largeur (en cm)": "Width (cm)",
        "Hauteur (en cm)": "Height (cm)",
        "Catégories": "Categories",
        "Parent": "Parent",
        "Images": "Images",
        "Garantie": "Warranty",
        "Pays de fabrication": "Country of manufacture",
        "Marque": "Brands"
    }
    df.rename(columns=correspondance_woocommerce, inplace=True)
    return df

def supprimer_doublons_colonnes(df):
    correspondance_woocommerce = {
        "Référence": "SKU",
        "Nom de l'article (en Français)": "Name",
        "Description courte (en Français)": "Short description",
        "Description (en Français)": "Description",
        "Prix pour le groupe Défaut": "Regular price",
        "Prix de vente conseillé": "Sale price",
        "Stock - Quantité": "Stock",
        "Option Couleur (en Français)": "Attribute 1 value(s)",
        "Option Taille (en Français)": "Attribute 2 value(s)",
        "Poids (en Kg)": "Weight (kg)",
        "Longueur (en cm)": "Length (cm)",
        "Largeur (en cm)": "Width (cm)",
        "Hauteur (en cm)": "Height (cm)",
        "Catégories": "Categories",
        "Parent": "Parent",
        "Images": "Images",
        "Garantie": "Warranty",
        "Pays de fabrication": "Country of manufacture",
        "Marque": "Brands"
    }
    colonnes_presentes = df.columns
    colonnes_a_supprimer = [
        fr_col for fr_col, en_col in correspondance_woocommerce.items() 
        if fr_col in colonnes_presentes and en_col in colonnes_presentes
    ]
    df.drop(columns=colonnes_a_supprimer, inplace=True, errors='ignore')
    return df

def ajuster_categories(df):
    colonnes_categories = [
        'Nom de la catégorie de niveau 1 (en Français)',
        'Nom de la catégorie de niveau 2 (en Français)',
        'Nom de la catégorie de niveau 3 (en Français)',
        'Nom de la catégorie de niveau 4 (en Français)',
    ]
    colonnes_existantes = [col for col in colonnes_categories if col in df.columns]
    if colonnes_existantes:
        df['Categories'] = df[colonnes_existantes].apply(lambda x: ' > '.join(x.dropna()), axis=1)
    if 'Catégorie principale du produit' in df.columns:
        df['Categories'] = df.apply(
            lambda x: f"{x['Categories']} | {x['Catégorie principale du produit']}" 
            if pd.notnull(x['Catégorie principale du produit']) else x['Categories'],
            axis=1
        )
    df.drop(columns=colonnes_existantes + ['Catégorie principale du produit'], inplace=True, errors='ignore')
    return df

def formatter_images(df, taille_lot=100):
    base_url = "https://dev.yolobaby.online/wp-content/uploads/image-site/"
    
    colonnes_images = [
        "Image principale",
        "Image supplémentaire n°1",
        "Image supplémentaire n°2",
        "Image supplémentaire n°3",
        "Image supplémentaire n°4",
        "Image supplémentaire n°5",
        "Image supplémentaire n°6",
        "Image supplémentaire n°7",
        "Image supplémentaire n°8",
        "Image supplémentaire n°9"
    ]
    
    colonnes_existantes = [col for col in colonnes_images if col in df.columns]

    if not colonnes_existantes:
        print("⚠️ Aucune colonne d'image trouvée.")
        return df

    # Fusion des URLs complètes dans une nouvelle colonne temporaire
    df["all_image_urls"] = df[colonnes_existantes].apply(
        lambda row: [base_url + img.strip() for img in row.dropna().astype(str)], axis=1
    )

    # Génération directe de la colonne "Images"
    df["Images"] = df["all_image_urls"].apply(lambda urls: ", ".join(urls))

    # --- 👇 Partie désactivée : récupération des IDs depuis l’API + images supplémentaires ---

    # Créer une liste unique de toutes les URLs pour minimiser les appels API
    # toutes_urls = list(set(url for sublist in df["all_image_urls"] for url in sublist))

    # Récupérer les IDs en batch depuis l'API
    # url_to_id = recuperer_id_images_wp_via_api_batch(toutes_urls, taille_lot)

    # Associer les IDs récupérés aux URLs dans le DataFrame
    # def generer_meta(row):
    #     urls_sup = row["all_image_urls"][1:]  # images supplémentaires uniquement
    #     ids_sup = [str(url_to_id[url]) for url in urls_sup if url in url_to_id]
    #     return ",".join(ids_sup)

    # df["_wc_additional_variation_images"] = df.apply(generer_meta, axis=1)

    # --- ☝️ Fin de la partie désactivée ---

    # Nettoyage
    df.drop(
        columns=colonnes_existantes + ["all_image_urls"], inplace=True, errors="ignore"
    )

    return df


# --- 👇 Fonction API désactivée mais conservée si besoin futur ---
# def recuperer_id_images_wp_via_api_batch(urls, taille_lot=100):
#     api_url = "https://dev.yolobaby.online/api-images.php"
#     url_to_id = {}

#     for i in range(0, len(urls), taille_lot):
#         lot_urls = urls[i : i + taille_lot]
#         try:
#             response = requests.post(
#                 api_url, json={"urls": lot_urls, "api_key": "12345"}
#             )
#             response.raise_for_status()
#             resultat = response.json()
#             url_to_id.update(resultat)
#             print(
#                 f"✅ Lot {i // taille_lot + 1}/{(len(urls) - 1) // taille_lot + 1} traité avec succès."
#             )
#         except requests.RequestException as e:
#             print(f"❌ Erreur API sur le lot {i // taille_lot + 1}: {e}")
#             print(f"Réponse reçue : {response.text}")
#             sleep(1)  # Pause en cas d'erreur pour éviter surcharge API

#     return url_to_id

#
############################################
# Fonctions de détection/extraction des couleurs
############################################

def detecter_toutes_couleurs(nom_produit: str):
    if not isinstance(nom_produit, str):
        return []
    
    tokens = re.split(r"[\s\-\|\(\),/]+", nom_produit.lower())
    trouvees = [mapping_couleurs[t] for t in tokens if t in mapping_couleurs]

    return list(dict.fromkeys(trouvees))  # Supprime les doublons

# 📌 Fonction pour normaliser une liste de couleurs
def normaliser_liste_couleurs(couleurs_brutes: list):
    if not couleurs_brutes:
        return ""
    return ", ".join(dict.fromkeys([mapping_couleurs.get(c.lower(), "Non spécifiée").title() for c in couleurs_brutes]))

# 📌 Fonction pour nettoyer le nom du produit en supprimant la couleur
def nettoyer_nom_produit(nom_produit: str, couleurs: list):
    if not isinstance(nom_produit, str):
        return nom_produit
    # On retire d'abord les couleurs (s'il y en a) en tant que mots entiers
    for couleur in couleurs:
        nom_produit = re.sub(rf"\b{couleur}\b", "", nom_produit, flags=re.IGNORECASE)
    # Puis, si le nom contient " - ", on prend uniquement la partie avant
    if " - " in nom_produit:
        nom_produit = nom_produit.split(" - ")[0]
    # Enfin, on nettoie les espaces superflus et d'éventuels tirets en fin de chaîne
    nom_produit = re.sub(r'[-\s]+$', '', nom_produit)
    return re.sub(r'\s+', ' ', nom_produit).strip()

# 📌 Fonction pour détecter les produits composites
def extraire_couleurs_composite(nom_produit: str):
    """
    Extrait les couleurs liées aux éléments "Châssis" et "Siège".
    Un produit est considéré composite s'il a **Châssis** et **Siège** dans le même nom.
    """

    if not isinstance(nom_produit, str):
        return {}

    # Normalisation du texte (supprimer accents et mettre en minuscule)
    nom_lower = unicodedata.normalize("NFKD", nom_produit).encode("ASCII", "ignore").decode("utf-8").lower()
    resultat = {}

    # Définition des éléments à rechercher
    elements_couleur = {
        "Châssis": ["châssis", "chassis"],
        "Siège": ["siège", "siege", "assise"]
    }

    # Vérification de la présence des deux termes dans le même nom de produit
    contient_chassis = any(mot in nom_lower for mot in elements_couleur["Châssis"])
    contient_siege = any(mot in nom_lower for mot in elements_couleur["Siège"])

    if not (contient_chassis and contient_siege):
        return {}  # Pas un produit composite

    # Définition des adjectifs ignorés
    adjectifs_ignores = [
    "light", "pale", "deep", "bright", "medium",
    "fonce", "foncé", "clair", "pâle", "flashy", "fluorescent",
    "cozy", "mirage", "sepia", "peach", "magic", "canvas", "navy"
    "fog", "stormy", "almond", "leaf", "navy","candy", "fog", "almond", "canvas"
    
    # Ajout des adjectifs liés au Châssis
    "chrome", "matt", "matté", "brillant", "argenté", "dark", "magic"
    ]

    # Recherche des couleurs pour chaque élément
    for nom_element, variantes in elements_couleur.items():
        for variante in variantes:
            # Correction du regex pour éviter l'erreur "no such group"
            regex_patterns = [
                rf"{variante}\s+(?:({'|'.join(adjectifs_ignores)})\s+)?({'|'.join(couleurs_base)})",
                rf"({'|'.join(couleurs_base)})\s+{variante}"
            ]
            for regex in regex_patterns:
                match = re.search(regex, nom_lower, re.IGNORECASE)
                if match:
                    # Vérification si l'adjectif est capturé
                    couleur_brute = match.group(2) if match.lastindex == 2 else match.group(1)
                    couleur_normalisee = mapping_couleurs.get(couleur_brute, couleur_brute).title()
                    resultat[nom_element] = couleur_normalisee
                    break  # Sortir dès qu'une couleur est trouvée

    return resultat

  # Renvoie un dictionnaire contenant les couleurs détectées
def determiner_si_variable(nom_produit: str, option_taille: str = ""):
    """
    Un produit est variable s’il :
    - contient exactement une couleur détectée dans son nom
    - ou s’il a une taille détectée via un pattern intelligent
    """
    couleurs_detectees = detecter_toutes_couleurs(nom_produit)

    # Sécurisation max ici 👇
    taille = str(option_taille).strip().lower() if pd.notnull(option_taille) else ""

    contient_taille = bool(re.search(r"(mois|ans|m|t)", taille)) and len(taille) <= 10

    return len(couleurs_detectees) == 1 or contient_taille



# 📌 Fonction pour regrouper les produits **variables** par couleur


def regrouper_variations_par_couleur(df):
    """
    Regroupe les produits par modèle (basé sur le nom nettoyé sans couleur).

    - Même s’il n’y a qu’un seul produit avec une couleur, on le traite comme un produit variable
      avec une seule variation.
    """
    # 1) Regrouper par nom nettoyé (sans couleur)
    groupes = {}
    for _, row in df.iterrows():
        nom_original = str(row["Name"])
        couleurs_detectees = detecter_toutes_couleurs(nom_original)
        nom_sans_couleur = nettoyer_nom_produit(nom_original, couleurs_detectees).strip()
        key = nom_sans_couleur.lower()
        groupes.setdefault(key, []).append(row)
    
    liste_resultats = []

    # 2) Traiter chaque groupe
    for key, rows in groupes.items():
        couleurs_group = set()
        for row in rows:
            couleurs = detecter_toutes_couleurs(str(row["Name"]))
            couleurs_group.update(couleurs)
        couleurs_group_list = list(couleurs_group)

        # ✅ Cas 1 : groupe avec un seul produit mais une couleur détectée → variable avec 1 variation
        if len(rows) == 1 and len(couleurs_group_list) == 1:
            row = rows[0]
            parent = row.copy()
            variation = row.copy()

            sku_orig = str(row["SKU"])
            parent["SKU"] = "PARENT-" + sku_orig
            parent["Name"] = nettoyer_nom_produit(row["Name"], couleurs_group_list).strip()
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s"] = normaliser_liste_couleurs(couleurs_group_list)
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)

            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 1 name"] = "Couleur"
            variation["Attribute 1 value(s"] = normaliser_liste_couleurs(couleurs_group_list)
            variation["Attribute 1 visible"] = "yes"
            variation["Attribute 1 global"] = "yes"
            variation["SKU"] = sku_orig + "-V1"  # suffixe pour unicité
            liste_resultats.append(variation)

        # ✅ Cas 2 : plusieurs produits → produit variable avec variations multiples
        elif len(rows) > 1:
            parent = rows[0].copy()
            sku_orig = str(parent["SKU"])
            parent["SKU"] = "PARENT-" + sku_orig
            parent["Name"] = nettoyer_nom_produit(parent["Name"], detecter_toutes_couleurs(parent["Name"])).strip()
            parent["Type"] = "variable"
            parent["Attribute 1 name"] = "Couleur"
            parent["Attribute 1 value(s"] = normaliser_liste_couleurs(couleurs_group_list)
            parent["Attribute 1 visible"] = "yes"
            parent["Attribute 1 global"] = "yes"
            parent["Code EAN"] = ""
            parent["Parent SKU"] = ""
            liste_resultats.append(parent)

            for row in rows:
                variation = row.copy()
                variation["Type"] = "variation"
                variation["Parent SKU"] = parent["SKU"]
                var_couleurs = detecter_toutes_couleurs(str(variation["Name"]))
                variation["Attribute 1 name"] = "Couleur"
                variation["Attribute 1 value(s"] = normaliser_liste_couleurs(var_couleurs)
                variation["Attribute 1 visible"] = "yes"
                variation["Attribute 1 global"] = "yes"
                if str(variation["SKU"]) == sku_orig:
                    suffix = var_couleurs[0][:2].upper() if var_couleurs else "XX"
                    variation["SKU"] = sku_orig + suffix
                liste_resultats.append(variation)

        # ❌ Cas inattendu (aucune couleur trouvée ou vide)
        else:
            print(f"ℹ️ Groupe ignoré (pas de couleur détectée) : {key}")

    df_final = pd.DataFrame(liste_resultats)
    return df_final


def regrouper_variations_par_taille(df):
    """
    Regroupe les produits variables par taille.
    """
    groupes = {}

    for _, row in df.iterrows():
        nom_original = str(row["Name"])
        taille_raw = row.get("Attribute 2 value(s)", "")
        taille = str(taille_raw).strip() if pd.notnull(taille_raw) else ""
        nom_base = re.sub(rf"\b{re.escape(taille)}\b", "", nom_original, flags=re.IGNORECASE).strip()
        groupes.setdefault(nom_base.lower(), []).append(row)

    liste_resultats = []

    for ref, rows in groupes.items():
        tailles_group = set()
        for row in rows:
            taille_raw = row.get("Attribute 2 value(s)", "")
            taille = str(taille_raw).strip() if pd.notnull(taille_raw) else ""
            if taille:
                tailles_group.add(taille)
        tailles_group_list = sorted(list(tailles_group))

        parent = rows[0].copy()
        sku_orig = str(parent["SKU"]).strip()
        parent["SKU"] = "PARENT-" + sku_orig
        parent["Type"] = "variable"
        parent["Attribute 2 name"] = "Taille"
        parent["Attribute 2 value(s)"] = ", ".join(tailles_group_list)
        parent["Attribute 2 visible"] = "yes"
        parent["Attribute 2 global"] = "yes"
        parent["Parent SKU"] = ""
        if "EAN" in parent:
            parent["EAN"] = ""
        elif "Code EAN" in parent:
            parent["Code EAN"] = ""
        liste_resultats.append(parent)

        for row in rows:
            variation = row.copy()
            variation["Type"] = "variation"
            variation["Parent SKU"] = parent["SKU"]
            variation["Attribute 2 name"] = "Taille"
            taille_raw = variation.get("Attribute 2 value(s)", "")
            taille = str(taille_raw).strip() if pd.notnull(taille_raw) else ""
            variation["Attribute 2 value(s)"] = taille
            variation["Attribute 2 visible"] = "yes"
            variation["Attribute 2 global"] = "yes"

            if str(variation["SKU"]).strip() == sku_orig:
                suffix = taille[:2].upper() if taille else "XX"
                variation["SKU"] = sku_orig + suffix

            liste_resultats.append(variation)

    return pd.DataFrame(liste_resultats)


def main():
    root = Tk()
    root.withdraw()

    # 📂 Sélection du fichier CSV
    chemin_fichier = filedialog.askopenfilename(
        filetypes=[("CSV Files", "*.csv")],
        title="Sélectionnez le fichier CSV"
    )
    if not chemin_fichier:
        print("❌ Aucun fichier sélectionné. Fermeture du script.")
        return

    try:
        # Chargement du fichier avec encodage UTF-8
        df = pd.read_csv(chemin_fichier, encoding="utf-8-sig", dtype=str)
        print(f"📂 Fichier chargé : {os.path.basename(chemin_fichier)}")

        df.columns = df.columns.str.strip()
        print("🔍 Colonnes détectées :", df.columns.tolist())

        df = renommer_colonnes_pour_woocommerce(df)
        print("✅ Colonnes après renommage :", df.columns.tolist())

        if "Name" not in df.columns:
            raise KeyError(f"❌ La colonne 'Name' est absente après transformation ! Colonnes actuelles : {df.columns.tolist()}")

        # S'assurer que la colonne "Attribute 2 value(s)" existe
        if "Attribute 2 value(s)" not in df.columns:
            df["Attribute 2 value(s)"] = ""

        # 💥 Forcer la colonne à être du texte nettoyé
        df["Attribute 2 value(s)"] = df["Attribute 2 value(s)"].fillna("").astype(str).apply(str.strip)

        df = supprimer_doublons_colonnes(df)
        print("✅ Colonnes après suppression des doublons :", df.columns.tolist())

        df = ajuster_categories(df)
        df = formatter_images(df, taille_lot=50)

        # Détection des produits composites et définition du type
        df["Composants composites (encodés en JSON)"] = df["Name"].apply(extraire_couleurs_composite)
        df["Type"] = df["Composants composites (encodés en JSON)"].apply(
            lambda x: "composite" if len(x) > 0 else "variable"
        )

        # Séparation entre produits composites et produits variables
        df_composites = df[df["Type"] == "composite"]
        df_variables = df[df["Type"] == "variable"]

        print(f"🛠️ Produits composites détectés : {len(df_composites)}")
        print(f"🛠️ Produits variables détectés : {len(df_variables)}")

        # ✅ Marquage avec protection contre NaN
        df_variables["Is_Variable"] = df_variables.apply(
            lambda row: determiner_si_variable(
                str(row["Name"]),
                str(row.get("Attribute 2 value(s)", "")).strip() if pd.notnull(row.get("Attribute 2 value(s)")) else ""
            ),
            axis=1
        )

        df_variables_reels = df_variables[df_variables["Is_Variable"]]
        print(f"✅ Produits variables réellement éligibles : {len(df_variables_reels)}")

        # Séparation selon la présence d'une option taille dans "Attribute 2 value(s)"
        df_has_size = df_variables_reels[
            df_variables_reels["Attribute 2 value(s)"].notna() & 
            (df_variables_reels["Attribute 2 value(s)"].str.strip() != "")
        ]
        df_without_size = df_variables_reels[
            df_variables_reels["Attribute 2 value(s)"].isna() | 
            (df_variables_reels["Attribute 2 value(s)"].str.strip() == "")
        ]

        # Traitement des produits variables dotés d'une option taille (regroupement par taille)
        if not df_has_size.empty:
            df_grouped_size = regrouper_variations_par_taille(df_has_size)
            print(f"✅ Produits variables regroupés par taille : {len(df_grouped_size)}")
        else:
            df_grouped_size = pd.DataFrame()
            print("ℹ️ Aucun produit avec option taille détecté.")

        # Traitement des produits variables sans option taille (regroupement par couleur)
        if not df_without_size.empty:
            df_grouped_color = regrouper_variations_par_couleur(df_without_size)
            print(f"✅ Produits variables regroupés par couleur : {len(df_grouped_color)}")
        else:
            df_grouped_color = pd.DataFrame()
            print("ℹ️ Aucun produit sans option taille détecté, regroupement couleur non nécessaire.")

        # Fusion de tous les produits finaux (composites, variables par taille et par couleur)
        df_final = pd.concat([df_composites, df_grouped_size, df_grouped_color], ignore_index=True)

        # Export du fichier final
        nouveau_chemin = os.path.splitext(chemin_fichier)[0] + "_final.csv"
        df_final.to_csv(nouveau_chemin, index=False, sep=",", encoding="utf-8-sig")
        print(f"✅ Fichier final exporté avec toutes les données : {nouveau_chemin}")

    except Exception as e:
        print(f"❌ Erreur pendant le traitement : {e}")

if __name__ == "__main__":
    main()
